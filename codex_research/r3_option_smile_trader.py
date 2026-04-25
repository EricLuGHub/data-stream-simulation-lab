from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
import json
import math


UNDERLYING = "VELVETFRUIT_EXTRACT"
VOUCHERS = {
    "VEV_4000": (4000.0, 0.495),
    "VEV_4500": (4500.0, 0.285),
    "VEV_5000": (5000.0, 0.225),
    "VEV_5100": (5100.0, 0.225),
    "VEV_5200": (5200.0, 0.225),
    "VEV_5300": (5300.0, 0.225),
    "VEV_5400": (5400.0, 0.210),
    # 5500 has a clean formula fit but poor fill economics in the public trade
    # simulator, so the deployed strategy leaves it alone.
    "VEV_6000": (6000.0, 0.345),
    "VEV_6500": (6500.0, 0.520),
}
LIMIT = {p: 200 for p in VOUCHERS}
TAU_SCALE = 290.0


class Trader:
    def run(self, state: TradingState):
        data = self._load(state.traderData)
        day = self._infer_day(data, state.timestamp)
        result: Dict[str, List[Order]] = {}

        spot = self._mid(state.order_depths.get(UNDERLYING))
        if spot is None:
            return result, 0, json.dumps(data)

        # The public data has days 0, 1, 2 with decreasing option maturity.
        # If a backtest concatenates days with monotonically increasing timestamps,
        # the day is inferred from million-timestamp buckets. If it preserves
        # original timestamps, rollover detection increments it.
        tau = max((7.0 - day) / TAU_SCALE, 1e-5)

        for product, (strike, sigma) in VOUCHERS.items():
            od = state.order_depths.get(product)
            if od is None or not od.buy_orders or not od.sell_orders:
                continue

            fair = self._call_price(spot, strike, tau, sigma)
            best_bid = max(od.buy_orders)
            best_ask = min(od.sell_orders)
            spread = best_ask - best_bid
            edge = self._edge(product, spread)
            pos = state.position.get(product, 0)
            orders: List[Order] = []

            if best_ask < fair - edge:
                qty = min(-od.sell_orders[best_ask], LIMIT[product] - pos, self._take_cap(product))
                if qty > 0:
                    orders.append(Order(product, best_ask, qty))
                    pos += qty

            if best_bid > fair + edge:
                qty = min(od.buy_orders[best_bid], LIMIT[product] + pos, self._take_cap(product))
                if qty > 0:
                    orders.append(Order(product, best_bid, -qty))
                    pos -= qty

            # Join near the fair value when the model is comfortably inside the
            # spread. This captures fills from public trades without crossing.
            inv = pos / LIMIT[product]
            bid_px = math.floor(fair - edge * 0.55 - 1.5 * inv)
            ask_px = math.ceil(fair + edge * 0.55 - 1.5 * inv)
            if bid_px >= ask_px:
                bid_px = ask_px - 1
            if bid_px > best_bid and bid_px < best_ask and pos < LIMIT[product]:
                orders.append(Order(product, bid_px, min(18, LIMIT[product] - pos)))
            if ask_px < best_ask and ask_px > best_bid and pos > -LIMIT[product]:
                orders.append(Order(product, ask_px, -min(18, LIMIT[product] + pos)))

            if orders:
                result[product] = orders

        data["last_ts"] = state.timestamp
        data["day"] = day
        return result, 0, json.dumps(data)

    def _infer_day(self, data, timestamp: int) -> int:
        if timestamp >= 1_000_000:
            return int(timestamp // 1_000_000)
        day = int(data.get("day", 0))
        last = data.get("last_ts")
        if last is not None and timestamp < int(last):
            day += 1
        return max(0, min(6, day))

    def _edge(self, product: str, spread: int) -> float:
        if product in ("VEV_4000", "VEV_4500", "VEV_5500"):
            return max(0.7, 0.18 * spread)
        if product in ("VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400"):
            return max(1.0, 0.22 * spread)
        return 0.8

    def _take_cap(self, product: str) -> int:
        if product in ("VEV_6000", "VEV_6500"):
            return 8
        if product in ("VEV_4000", "VEV_4500", "VEV_5500"):
            return 24
        return 18

    def _mid(self, od: OrderDepth | None):
        if od is None or not od.buy_orders or not od.sell_orders:
            return None
        return 0.5 * (max(od.buy_orders) + min(od.sell_orders))

    def _call_price(self, s: float, k: float, tau: float, sigma: float) -> float:
        vol_t = sigma * math.sqrt(tau)
        d1 = (math.log(s / k) + 0.5 * sigma * sigma * tau) / vol_t
        d2 = d1 - vol_t
        return s * self._norm_cdf(d1) - k * self._norm_cdf(d2)

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _load(self, raw: str):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}
