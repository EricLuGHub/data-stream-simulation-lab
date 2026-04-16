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
        spread = best_ask - best_bid

        prev_mid = td.get("prev_mid", mid)
        ret = mid - prev_mid
        td["prev_mid"] = mid

        ret_hist = td.get("ret_hist", [])
        ret_hist.append(ret)
        if len(ret_hist) > 30:
            ret_hist = ret_hist[-30:]
        td["ret_hist"] = ret_hist

        vol = self._std(ret_hist[-12:]) if len(ret_hist) >= 4 else 0.0
        ema = 0.3 * mid + 0.7 * td.get("ema", mid)
        td["ema"] = ema

        imbalance = self._imbalance(od)
        fair = ema + 0.7 * imbalance

        # Regime selection from spread and realized micro-vol.
        if spread <= 8 and vol <= 2.5:
            half_spread = 1
            take_width = 0
            base_size = 16
        elif spread <= 14 and vol <= 4.0:
            half_spread = 2
            take_width = 1
            base_size = 22
        else:
            half_spread = 3
            take_width = 2
            base_size = 26

        # Edge-taking layer.
        pos, take_orders = self._take(od, fair, pos, take_width)
        orders.extend(take_orders)

        # Make layer with inventory-aware fair shift.
        inv_ratio = pos / LIMIT
        fair_adj = fair - 3.0 * inv_ratio

        bid_px = math.floor(fair_adj - half_spread)
        ask_px = math.ceil(fair_adj + half_spread)

        if best_bid + 1 < fair_adj:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 1 > fair_adj:
            ask_px = min(ask_px, best_ask - 1)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_qty = min(buy_cap, max(0, int(base_size * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(0, int(base_size * (1 + inv_ratio))))

        if abs(pos) >= 38:
            if pos > 0:
                buy_qty = 0
                sell_qty = min(sell_cap, sell_qty + 12)
            else:
                sell_qty = 0
                buy_qty = min(buy_cap, buy_qty + 12)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(td)

    def _imbalance(self, od: OrderDepth):
        b = sum(od.buy_orders.values())
        a = sum(-v for v in od.sell_orders.values())
        d = b + a
        if d == 0:
            return 0.0
        return (b - a) / d

    def _take(self, od: OrderDepth, fair: float, pos: int, width: int):
        orders: List[Order] = []

        for ask, vol in sorted(od.sell_orders.items()):
            if ask <= fair - width:
                qty = min(-vol, LIMIT - pos)
                if qty > 0:
                    orders.append(Order(ASH, ask, qty))
                    pos += qty

        for bid, vol in sorted(od.buy_orders.items(), reverse=True):
            if bid >= fair + width:
                qty = min(vol, LIMIT + pos)
                if qty > 0:
                    orders.append(Order(ASH, bid, -qty))
                    pos -= qty

        return pos, orders

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
