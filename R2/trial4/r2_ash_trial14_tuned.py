from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
    """R2 Trial 4: trial14-style ASH with mild parameter tuning."""

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

        ema = 0.26 * mid + 0.74 * td.get("ema", mid)
        td["ema"] = ema
        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-40:]
        td["mid_hist"] = mids

        short = mids[-9:] if len(mids) >= 9 else mids
        long = mids[-22:] if len(mids) >= 22 else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

        wall_bid, wall_ask = self._get_walls(od, 11)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        fair = 0.53 * wall_mid + 0.27 * ema + 0.2 * (0.6 * short_mean + 0.4 * long_mean) + 0.5 * imb

        take_width = 1 if abs(z) < 1.1 else 0
        pos, take_orders = self._take(od, fair, pos, take_width, take_cap=5)
        orders.extend(take_orders)

        inv = pos / LIMIT
        half_spread = 3 if spread <= 11 else 4
        bid_px = math.floor(fair - half_spread - 3.6 * inv)
        ask_px = math.ceil(fair + half_spread - 3.6 * inv)

        if best_bid + 2 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 2 > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        base = 15
        buy_qty = min(buy_cap, max(0, int(base * (1 - 0.75 * inv))))
        sell_qty = min(sell_cap, max(0, int(base * (1 + 0.72 * inv))))

        if pos > 34 or z > 1.7:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 7)
        elif pos < -34 or z < -1.7:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 7)

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

    def _take(self, od: OrderDepth, fair: float, pos: int, width: int, take_cap: int):
        orders: List[Order] = []
        for ask, vol in sorted(od.sell_orders.items()):
            if ask <= fair - width:
                qty = min(-vol, LIMIT - pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, ask, qty))
                    pos += qty
        for bid, vol in sorted(od.buy_orders.items(), reverse=True):
            if bid >= fair + width:
                qty = min(vol, LIMIT + pos, take_cap)
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
