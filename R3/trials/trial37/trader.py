from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
import json
import math


PRODUCT = "HYDROGEL_PACK"
LIMIT = 200
EMA_ALPHA = 0.12
SIGNAL_WEIGHT = 1.6
TAKE_EDGE = 1.4
MAKE_EDGE = 1.9
INVENTORY_SKEW = 1.8
SIGNAL_GATE = 0.03
MAX_TAKE = 12
QUOTE_SIZE = 14


class Trader:
    def run(self, state: TradingState):
        data = self._load(state.traderData)
        od = state.order_depths.get(PRODUCT)
        if od is None or not od.buy_orders or not od.sell_orders:
            return {}, 0, json.dumps(data)

        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid
        imbalance = self._imbalance(od)

        ema = float(data.get("ema", mid))
        ema = (1.0 - EMA_ALPHA) * ema + EMA_ALPHA * mid
        fair = ema + SIGNAL_WEIGHT * imbalance * max(1.0, spread)

        pos = state.position.get(PRODUCT, 0)
        orders: List[Order] = []

        if imbalance > SIGNAL_GATE and best_ask < fair - TAKE_EDGE:
            qty = min(-od.sell_orders[best_ask], LIMIT - pos, MAX_TAKE)
            if qty > 0:
                orders.append(Order(PRODUCT, best_ask, qty))
                pos += qty

        if imbalance < -SIGNAL_GATE and best_bid > fair + TAKE_EDGE:
            qty = min(od.buy_orders[best_bid], LIMIT + pos, MAX_TAKE)
            if qty > 0:
                orders.append(Order(PRODUCT, best_bid, -qty))
                pos -= qty

        inv = pos / LIMIT
        bid_px = math.floor(fair - MAKE_EDGE - INVENTORY_SKEW * inv)
        ask_px = math.ceil(fair + MAKE_EDGE - INVENTORY_SKEW * inv)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        if best_bid < bid_px < best_ask and pos < LIMIT:
            orders.append(Order(PRODUCT, bid_px, min(QUOTE_SIZE, LIMIT - pos)))
        if best_bid < ask_px < best_ask and pos > -LIMIT:
            orders.append(Order(PRODUCT, ask_px, -min(QUOTE_SIZE, LIMIT + pos)))

        result: Dict[str, List[Order]] = {}
        if orders:
            result[PRODUCT] = orders

        data["ema"] = ema
        return result, 0, json.dumps(data)

    def _imbalance(self, od: OrderDepth) -> float:
        bid_vol = float(od.buy_orders[max(od.buy_orders)])
        ask_vol = float(-od.sell_orders[min(od.sell_orders)])
        den = bid_vol + ask_vol
        if den <= 0.0:
            return 0.0
        return (bid_vol - ask_vol) / den

    def _load(self, raw: str):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}
