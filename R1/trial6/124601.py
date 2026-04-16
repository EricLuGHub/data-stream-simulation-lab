from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
    def run(self, state: TradingState):
        trader_data = {}
        if state.traderData:
            try:
                trader_data = json.loads(state.traderData)
            except Exception:
                trader_data = {}

        result: Dict[str, List[Order]] = {}
        if ASH not in state.order_depths:
            return result, 0, json.dumps(trader_data)

        od = state.order_depths[ASH]
        pos = state.position.get(ASH, 0)
        orders: List[Order] = []

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None or best_ask is None:
            result[ASH] = []
            return result, 0, json.dumps(trader_data)

        wall_bid, wall_ask = self._get_walls(od, min_wall_volume=12)
        fair = (wall_bid + wall_ask) / 2

        # 1) Take clear edge first.
        pos, take_orders = self._take(ASH, od, fair, pos, take_width=1)
        orders.extend(take_orders)

        # 2) Flatten if inventory drifts too far.
        if pos > 30 and best_bid >= math.floor(fair):
            qty = min(pos - 25, od.buy_orders.get(best_bid, 0))
            if qty > 0:
                orders.append(Order(ASH, best_bid, -qty))
                pos -= qty
        elif pos < -30 and best_ask <= math.ceil(fair):
            qty = min(-pos - 25, -od.sell_orders.get(best_ask, 0))
            if qty > 0:
                orders.append(Order(ASH, best_ask, qty))
                pos += qty

        # 3) Post make quotes around fair, one-tick improved when safe.
        inv_skew = -pos / LIMIT
        bid_px = math.floor(fair - 2 + 2.0 * inv_skew)
        ask_px = math.ceil(fair + 2 + 2.0 * inv_skew)

        if best_bid is not None and best_bid + 1 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask is not None and best_ask - 1 > fair:
            ask_px = min(ask_px, best_ask - 1)

        if bid_px >= ask_px:
            bid_px = math.floor(fair - 1)
            ask_px = math.ceil(fair + 1)

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_qty = min(24, buy_cap)
        sell_qty = min(24, sell_cap)

        if pos < -20:
            buy_qty = min(buy_cap, buy_qty + 8)
            sell_qty = max(0, sell_qty - 8)
        elif pos > 20:
            sell_qty = min(sell_cap, sell_qty + 8)
            buy_qty = max(0, buy_qty - 8)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(trader_data)

    def _get_walls(self, od: OrderDepth, min_wall_volume: int) -> Tuple[int, int]:
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())

        bid_wall = best_bid
        for px, vol in sorted(od.buy_orders.items(), key=lambda x: x[0], reverse=True):
            if vol >= min_wall_volume:
                bid_wall = px
                break

        ask_wall = best_ask
        for px, vol in sorted(od.sell_orders.items(), key=lambda x: x[0]):
            if -vol >= min_wall_volume:
                ask_wall = px
                break

        return bid_wall, ask_wall

    def _take(self, product: str, od: OrderDepth, fair: float, pos: int, take_width: int):
        orders: List[Order] = []
        if od.sell_orders:
            for ask, vol in sorted(od.sell_orders.items()):
                if ask <= fair - take_width:
                    qty = min(-vol, LIMIT - pos)
                    if qty > 0:
                        orders.append(Order(product, ask, qty))
                        pos += qty

        if od.buy_orders:
            for bid, vol in sorted(od.buy_orders.items(), reverse=True):
                if bid >= fair + take_width:
                    qty = min(vol, LIMIT + pos)
                    if qty > 0:
                        orders.append(Order(product, bid, -qty))
                        pos -= qty

        return pos, orders

    def _clamp(self, orders: List[Order], cur_pos: int, limit: int) -> List[Order]:
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
