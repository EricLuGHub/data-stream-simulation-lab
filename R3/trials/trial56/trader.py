from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
import json
import math


UNDERLYING = "VELVETFRUIT_EXTRACT"
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
LIMIT_VEV = {k: 300 for k in VOUCHERS_BASE}
LIMIT_UNDERLYING = 200
TAU_SCALE = 250.0
SIGMA_SCALE = 1.05
EDGE_MULT = 1.1
JOIN_SIZE = 14
VELV_ENABLE = True
VELV_EMA_ALPHA = 0.08
VELV_SIGNAL_WEIGHT = 1.4
VELV_TAKE_EDGE = 1.3
VELV_MAKE_EDGE = 1.8
VELV_SIGNAL_GATE = 0.02
MAX_TAKE_WING = 10
MAX_TAKE_MID = 16
TRADED = ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_6000', 'VEV_6500']


class Trader:
    def run(self, state: TradingState):
        data = self._load(state.traderData)
        result: Dict[str, List[Order]] = {}

        spot_od = state.order_depths.get(UNDERLYING)
        if spot_od is None or not spot_od.buy_orders or not spot_od.sell_orders:
            return result, 0, json.dumps(data)

        day = self._infer_day(data, state.timestamp)
        tau = max((7.0 - day) / TAU_SCALE, 1e-5)
        spot_bid = max(spot_od.buy_orders)
        spot_ask = min(spot_od.sell_orders)
        spot = 0.5 * (spot_bid + spot_ask)

        if VELV_ENABLE:
            velv_orders = self._trade_underlying(state, data, spot_od, spot)
            if velv_orders:
                result[UNDERLYING] = velv_orders

        for product in TRADED:
            cfg = VOUCHERS_BASE[product]
            strike = cfg[0]
            sigma = cfg[1] * SIGMA_SCALE
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
                qty = min(-od.sell_orders[best_ask], LIMIT_VEV[product] - pos, take_cap)
                if qty > 0:
                    orders.append(Order(product, best_ask, qty))
                    pos += qty

            if best_bid > fair + edge:
                qty = min(od.buy_orders[best_bid], LIMIT_VEV[product] + pos, take_cap)
                if qty > 0:
                    orders.append(Order(product, best_bid, -qty))
                    pos -= qty

            inv = pos / LIMIT_VEV[product]
            bid_px = math.floor(fair - edge * 0.55 - 1.2 * inv)
            ask_px = math.ceil(fair + edge * 0.55 - 1.2 * inv)
            if bid_px >= ask_px:
                bid_px = ask_px - 1

            if best_bid < bid_px < best_ask and pos < LIMIT_VEV[product]:
                orders.append(Order(product, bid_px, min(JOIN_SIZE, LIMIT_VEV[product] - pos)))
            if best_bid < ask_px < best_ask and pos > -LIMIT_VEV[product]:
                orders.append(Order(product, ask_px, -min(JOIN_SIZE, LIMIT_VEV[product] + pos)))

            if orders:
                result[product] = orders

        data["last_ts"] = state.timestamp
        data["day"] = day
        return result, 0, json.dumps(data)

    def _trade_underlying(self, state: TradingState, data, od: OrderDepth, mid: float) -> List[Order]:
        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        spread = max(1, best_ask - best_bid)
        imb = self._imbalance(od)

        ema = float(data.get("velv_ema", mid))
        ema = (1.0 - VELV_EMA_ALPHA) * ema + VELV_EMA_ALPHA * mid
        fair = ema + VELV_SIGNAL_WEIGHT * imb * spread
        data["velv_ema"] = ema

        pos = state.position.get(UNDERLYING, 0)
        orders: List[Order] = []

        if imb > VELV_SIGNAL_GATE and best_ask < fair - VELV_TAKE_EDGE:
            qty = min(-od.sell_orders[best_ask], LIMIT_UNDERLYING - pos, 20)
            if qty > 0:
                orders.append(Order(UNDERLYING, best_ask, qty))
                pos += qty

        if imb < -VELV_SIGNAL_GATE and best_bid > fair + VELV_TAKE_EDGE:
            qty = min(od.buy_orders[best_bid], LIMIT_UNDERLYING + pos, 20)
            if qty > 0:
                orders.append(Order(UNDERLYING, best_bid, -qty))
                pos -= qty

        inv = pos / LIMIT_UNDERLYING
        bid_px = math.floor(fair - VELV_MAKE_EDGE - 1.0 * inv)
        ask_px = math.ceil(fair + VELV_MAKE_EDGE - 1.0 * inv)
        if best_bid < bid_px < best_ask and pos < LIMIT_UNDERLYING:
            orders.append(Order(UNDERLYING, bid_px, min(12, LIMIT_UNDERLYING - pos)))
        if best_bid < ask_px < best_ask and pos > -LIMIT_UNDERLYING:
            orders.append(Order(UNDERLYING, ask_px, -min(12, LIMIT_UNDERLYING + pos)))
        return orders

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
