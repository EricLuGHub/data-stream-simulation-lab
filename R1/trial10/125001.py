from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
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

        ret = mid - td.get("prev_mid", mid)
        td["prev_mid"] = mid
        ret_hist = td.get("ret_hist", [])
        ret_hist.append(ret)
        ret_hist = ret_hist[-30:]
        td["ret_hist"] = ret_hist

        vol = self._std(ret_hist[-12:]) if len(ret_hist) >= 4 else 0.0
        wall_bid, wall_ask = self._get_walls(od, min_wall_volume=12)
        wall_mid = 0.5 * (wall_bid + wall_ask)

        # Hybrid fair: wall-mid anchor + smooth EMA + imbalance tilt.
        ema = 0.35 * mid + 0.65 * td.get("ema", mid)
        td["ema"] = ema
        imb = self._imbalance(od)
        fair = 0.55 * wall_mid + 0.45 * ema + 0.6 * imb

        if spread <= 8 and vol <= 2.5:
            half_spread, take_width, base = 1, 0, 16
        elif spread <= 14 and vol <= 4.0:
            half_spread, take_width, base = 2, 1, 22
        else:
            half_spread, take_width, base = 3, 2, 26

        pos, take_orders = self._take(od, fair, pos, take_width)
        orders.extend(take_orders)

        # Inventory flattening from trial6 style.
        if pos > 32 and best_bid >= math.floor(fair):
            qty = min(pos - 26, od.buy_orders.get(best_bid, 0))
            if qty > 0:
                orders.append(Order(ASH, best_bid, -qty))
                pos -= qty
        elif pos < -32 and best_ask <= math.ceil(fair):
            qty = min(-pos - 26, -od.sell_orders.get(best_ask, 0))
            if qty > 0:
                orders.append(Order(ASH, best_ask, qty))
                pos += qty

        inv = pos / LIMIT
        fair_adj = fair - 3.0 * inv
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
        buy_qty = min(buy_cap, max(0, int(base * (1 - inv))))
        sell_qty = min(sell_cap, max(0, int(base * (1 + inv))))

        if abs(pos) >= 38:
            if pos > 0:
                buy_qty = 0
                sell_qty = min(sell_cap, sell_qty + 10)
            else:
                sell_qty = 0
                buy_qty = min(buy_cap, buy_qty + 10)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(td)

    def _load_td(self, raw: str):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _get_walls(self, od: OrderDepth, min_wall_volume: int) -> Tuple[int, int]:
        bid_wall = max(od.buy_orders.keys())
        ask_wall = min(od.sell_orders.keys())
        for p, v in sorted(od.buy_orders.items(), key=lambda x: x[0], reverse=True):
            if v >= min_wall_volume:
                bid_wall = p
                break
        for p, v in sorted(od.sell_orders.items(), key=lambda x: x[0]):
            if -v >= min_wall_volume:
                ask_wall = p
                break
        return bid_wall, ask_wall

    def _imbalance(self, od: OrderDepth):
        b = sum(od.buy_orders.values())
        a = sum(-v for v in od.sell_orders.values())
        d = b + a
        return 0.0 if d == 0 else (b - a) / d

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

    def _std(self, xs: List[float]):
        if not xs:
            return 0.0
        m = sum(xs) / len(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

    def _clamp(self, orders: List[Order], cur: int, limit: int):
        buy = sum(o.quantity for o in orders if o.quantity > 0)
        sell = sum(-o.quantity for o in orders if o.quantity < 0)
        if cur + buy > limit and buy > 0:
            s = max(0.0, (limit - cur) / buy)
            for o in orders:
                if o.quantity > 0:
                    o.quantity = int(o.quantity * s)
        if cur - sell < -limit and sell > 0:
            s = max(0.0, (limit + cur) / sell)
            for o in orders:
                if o.quantity < 0:
                    o.quantity = -int((-o.quantity) * s)
        return [o for o in orders if o.quantity != 0]
