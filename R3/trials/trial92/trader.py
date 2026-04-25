from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
import json
import math


PACK = "HYDROGEL_PACK"
VELV = "VELVETFRUIT_EXTRACT"

# Trial24 PACK params
PACK_LIMIT = 200
PACK_EMA_ALPHA = 0.12
PACK_SIGNAL_WEIGHT = 0.8
PACK_TAKE_EDGE = 0.8
PACK_MAKE_EDGE = 2.2
PACK_INVENTORY_SKEW = 2.2
PACK_SIGNAL_GATE = 0.05
PACK_MAX_TAKE = 10
PACK_QUOTE_SIZE = 12

# Trial72 VEV params (voucher-only)
VOUCHERS_BASE = {
    "VEV_4000": (4000.0, 0.495),
    "VEV_4500": (4500.0, 0.285),
    "VEV_5000": (5000.0, 0.225),
    "VEV_5100": (5100.0, 0.225),
    "VEV_5200": (5200.0, 0.225),
    "VEV_5300": (5300.0, 0.225),
    "VEV_5400": (5400.0, 0.210),
    "VEV_5500": (5500.0, 0.240),
    "VEV_6000": (6000.0, 0.345),
    "VEV_6500": (6500.0, 0.520),
}
VEV_LIMIT = {k: 300 for k in VOUCHERS_BASE}
TAU_SCALE = 320.0
SIGMA_SCALE = 1.05
EDGE_MULT = 0.85
JOIN_SIZE = 12
MAX_TAKE_WING = 8
MAX_TAKE_MID = 14
TRADED = ["VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_6000"]


class Trader:
    def run(self, state: TradingState):
        data = self._load(state.traderData)
        result: Dict[str, List[Order]] = {}

        pack_orders = self._trade_pack(state, data)
        if pack_orders:
            result[PACK] = pack_orders

        vev_orders = self._trade_vouchers(state, data)
        result.update(vev_orders)

        return result, 0, json.dumps(data)

    def _trade_pack(self, state: TradingState, data: dict) -> List[Order]:
        od = state.order_depths.get(PACK)
        if od is None or not od.buy_orders or not od.sell_orders:
            return []

        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid
        imbalance = self._imbalance(od)

        ema = float(data.get("pack_ema", mid))
        ema = (1.0 - PACK_EMA_ALPHA) * ema + PACK_EMA_ALPHA * mid
        fair = ema + PACK_SIGNAL_WEIGHT * imbalance * max(1.0, spread)

        pos = state.position.get(PACK, 0)
        orders: List[Order] = []

        if imbalance > PACK_SIGNAL_GATE and best_ask < fair - PACK_TAKE_EDGE:
            qty = min(-od.sell_orders[best_ask], PACK_LIMIT - pos, PACK_MAX_TAKE)
            if qty > 0:
                orders.append(Order(PACK, best_ask, qty))
                pos += qty

        if imbalance < -PACK_SIGNAL_GATE and best_bid > fair + PACK_TAKE_EDGE:
            qty = min(od.buy_orders[best_bid], PACK_LIMIT + pos, PACK_MAX_TAKE)
            if qty > 0:
                orders.append(Order(PACK, best_bid, -qty))
                pos -= qty

        inv = pos / PACK_LIMIT
        bid_px = math.floor(fair - PACK_MAKE_EDGE - PACK_INVENTORY_SKEW * inv)
        ask_px = math.ceil(fair + PACK_MAKE_EDGE - PACK_INVENTORY_SKEW * inv)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        if best_bid < bid_px < best_ask and pos < PACK_LIMIT:
            orders.append(Order(PACK, bid_px, min(PACK_QUOTE_SIZE, PACK_LIMIT - pos)))
        if best_bid < ask_px < best_ask and pos > -PACK_LIMIT:
            orders.append(Order(PACK, ask_px, -min(PACK_QUOTE_SIZE, PACK_LIMIT + pos)))

        data["pack_ema"] = ema
        return orders

    def _trade_vouchers(self, state: TradingState, data: dict) -> Dict[str, List[Order]]:
        out: Dict[str, List[Order]] = {}
        spot_od = state.order_depths.get(VELV)
        if spot_od is None or not spot_od.buy_orders or not spot_od.sell_orders:
            return out

        day = self._infer_day(data, state.timestamp)
        tau = max((7.0 - day) / TAU_SCALE, 1e-5)
        spot = 0.5 * (max(spot_od.buy_orders) + min(spot_od.sell_orders))

        for product in TRADED:
            strike, base_sigma = VOUCHERS_BASE[product]
            sigma = base_sigma * SIGMA_SCALE
            od = state.order_depths.get(product)
            if od is None or not od.buy_orders or not od.sell_orders:
                continue

            fair = self._call_price(spot, strike, tau, sigma)
            best_bid = max(od.buy_orders)
            best_ask = min(od.sell_orders)
            spread = max(1, best_ask - best_bid)
            edge = self._edge(product, spread)
            pos = state.position.get(product, 0)

            take_cap = MAX_TAKE_MID
            if product in ("VEV_4000", "VEV_4500", "VEV_6000", "VEV_6500"):
                take_cap = MAX_TAKE_WING

            orders: List[Order] = []
            if best_ask < fair - edge:
                qty = min(-od.sell_orders[best_ask], VEV_LIMIT[product] - pos, take_cap)
                if qty > 0:
                    orders.append(Order(product, best_ask, qty))
                    pos += qty

            if best_bid > fair + edge:
                qty = min(od.buy_orders[best_bid], VEV_LIMIT[product] + pos, take_cap)
                if qty > 0:
                    orders.append(Order(product, best_bid, -qty))
                    pos -= qty

            inv = pos / VEV_LIMIT[product]
            bid_px = math.floor(fair - edge * 0.55 - 1.2 * inv)
            ask_px = math.ceil(fair + edge * 0.55 - 1.2 * inv)
            if bid_px >= ask_px:
                bid_px = ask_px - 1

            if best_bid < bid_px < best_ask and pos < VEV_LIMIT[product]:
                orders.append(Order(product, bid_px, min(JOIN_SIZE, VEV_LIMIT[product] - pos)))
            if best_bid < ask_px < best_ask and pos > -VEV_LIMIT[product]:
                orders.append(Order(product, ask_px, -min(JOIN_SIZE, VEV_LIMIT[product] + pos)))

            if orders:
                out[product] = orders

        data["last_ts"] = state.timestamp
        data["day"] = day
        return out

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
            return EDGE_MULT * max(0.8, 0.18 * spread)
        if product in ("VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400"):
            return EDGE_MULT * max(1.0, 0.22 * spread)
        return EDGE_MULT * max(0.7, 0.16 * spread)

    def _imbalance(self, od: OrderDepth) -> float:
        bid_vol = float(od.buy_orders[max(od.buy_orders)])
        ask_vol = float(-od.sell_orders[min(od.sell_orders)])
        den = bid_vol + ask_vol
        if den <= 0.0:
            return 0.0
        return (bid_vol - ask_vol) / den

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
