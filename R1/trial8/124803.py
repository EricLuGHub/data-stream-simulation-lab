from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


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

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None or best_ask is None:
            result[ASH] = []
            return result, 0, json.dumps(td)

        mid = 0.5 * (best_bid + best_ask)

        mid_hist = td.get("mid_hist", [])
        mid_hist.append(mid)
        if len(mid_hist) > 25:
            mid_hist = mid_hist[-25:]
        td["mid_hist"] = mid_hist

        if len(mid_hist) >= 8:
            mean_mid = sum(mid_hist[-8:]) / 8
            std_mid = self._std(mid_hist[-8:])
        else:
            mean_mid = mid
            std_mid = 1.0

        z = 0.0 if std_mid <= 1e-6 else (mid - mean_mid) / std_mid
        fair = mean_mid

        # Reversion take logic when deviation is meaningful.
        if z >= 1.25:
            for bid, vol in sorted(od.buy_orders.items(), reverse=True):
                if bid >= fair:
                    qty = min(vol, LIMIT + pos)
                    if qty > 0:
                        orders.append(Order(ASH, bid, -qty))
                        pos -= qty
        elif z <= -1.25:
            for ask, vol in sorted(od.sell_orders.items()):
                if ask <= fair:
                    qty = min(-vol, LIMIT - pos)
                    if qty > 0:
                        orders.append(Order(ASH, ask, qty))
                        pos += qty

        # Inventory-aware market making around mean.
        inv_ratio = pos / LIMIT
        half_spread = 2 if abs(z) < 0.8 else 3

        bid_px = math.floor(fair - half_spread - 3.0 * inv_ratio)
        ask_px = math.ceil(fair + half_spread - 3.0 * inv_ratio)

        if best_bid + 1 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 1 > fair:
            ask_px = min(ask_px, best_ask - 1)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        base = 18
        buy_qty = min(buy_cap, base)
        sell_qty = min(sell_cap, base)

        # Strongly reduce quote on risk-increasing side when stretched.
        if pos >= 30:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 10)
        elif pos <= -30:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 10)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(td)

    def _std(self, xs: List[float]) -> float:
        if not xs:
            return 0.0
        m = sum(xs) / len(xs)
        v = sum((x - m) ** 2 for x in xs) / len(xs)
        return v ** 0.5

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
