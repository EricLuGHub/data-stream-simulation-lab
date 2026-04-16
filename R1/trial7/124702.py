from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50

PARAMS = {
    "ema_alpha": 0.35,
    "imbalance_weight": 0.9,
    "take_width": 1,
    "base_half_spread": 2,
    "base_size": 22,
    "inv_skew": 2.8,
}


class Trader:
    def run(self, state: TradingState):
        td = {}
        if state.traderData:
            try:
                td = json.loads(state.traderData)
            except Exception:
                td = {}

        result: Dict[str, List[Order]] = {}
        if ASH not in state.order_depths:
            return result, 0, json.dumps(td)

        od = state.order_depths[ASH]
        pos = state.position.get(ASH, 0)
        orders: List[Order] = []

        mid = self._mid(od)
        if mid is None:
            result[ASH] = []
            return result, 0, json.dumps(td)

        ema = PARAMS["ema_alpha"] * mid + (1 - PARAMS["ema_alpha"]) * td.get("ema", mid)
        td["ema"] = ema

        imbalance = self._imbalance(od)
        fair = ema + PARAMS["imbalance_weight"] * imbalance

        pos, take_orders = self._take_orders(od, fair, pos)
        orders.extend(take_orders)

        inv_ratio = pos / LIMIT
        half_spread = PARAMS["base_half_spread"]

        bid_px = math.floor(fair - half_spread - PARAMS["inv_skew"] * inv_ratio)
        ask_px = math.ceil(fair + half_spread - PARAMS["inv_skew"] * inv_ratio)

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else bid_px
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else ask_px

        # Improve queue position while preserving edge.
        if best_bid + 1 < fair - 0.5:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 1 > fair + 0.5:
            ask_px = min(ask_px, best_ask - 1)

        if bid_px >= ask_px:
            bid_px = min(bid_px, ask_px - 1)

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_qty = min(buy_cap, max(0, int(PARAMS["base_size"] * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(0, int(PARAMS["base_size"] * (1 + inv_ratio))))

        # Soft guardrails.
        if pos > 35:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 8)
        elif pos < -35:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 8)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(td)

    def _mid(self, od: OrderDepth):
        if not od.buy_orders or not od.sell_orders:
            return None
        return 0.5 * (max(od.buy_orders.keys()) + min(od.sell_orders.keys()))

    def _imbalance(self, od: OrderDepth):
        bid_vol = sum(od.buy_orders.values())
        ask_vol = sum(-v for v in od.sell_orders.values())
        den = bid_vol + ask_vol
        if den == 0:
            return 0.0
        return (bid_vol - ask_vol) / den

    def _take_orders(self, od: OrderDepth, fair: float, pos: int):
        orders: List[Order] = []
        tw = PARAMS["take_width"]

        for ask, vol in sorted(od.sell_orders.items()):
            if ask <= fair - tw:
                qty = min(-vol, LIMIT - pos)
                if qty > 0:
                    orders.append(Order(ASH, ask, qty))
                    pos += qty

        for bid, vol in sorted(od.buy_orders.items(), reverse=True):
            if bid >= fair + tw:
                qty = min(vol, LIMIT + pos)
                if qty > 0:
                    orders.append(Order(ASH, bid, -qty))
                    pos -= qty

        return pos, orders

    def _clamp(self, orders: List[Order], cur_pos: int, limit: int):
        buy_total = sum(o.quantity for o in orders if o.quantity > 0)
        sell_total = sum(-o.quantity for o in orders if o.quantity < 0)

        if cur_pos + buy_total > limit and buy_total > 0:
            scale = max(0.0, (limit - cur_pos) / buy_total)
            for o in orders:
                if o.quantity > 0:
                    o.quantity = int(o.quantity * scale)

        if cur_pos - sell_total < -limit and sell_total > 0:
            scale = max(0.0, (limit + cur_pos) / sell_total)
            for o in orders:
                if o.quantity < 0:
                    o.quantity = -int((-o.quantity) * scale)

        return [o for o in orders if o.quantity != 0]
