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
        wall_bid, wall_ask = self._get_walls(od, 10)
        wall_mid = 0.5 * (wall_bid + wall_ask)

        # EMA + imbalance component from trial7 family.
        ema = 0.35 * mid + 0.65 * td.get("ema", mid)
        td["ema"] = ema
        imb = self._imbalance(od)
        fair_base = ema + 0.9 * imb

        # z-score gate from trial8 family.
        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-25:]
        td["mid_hist"] = mids

        look = mids[-10:] if len(mids) >= 10 else mids
        mean_mid = sum(look) / len(look)
        std_mid = self._std(look)
        z = 0.0 if std_mid <= 1e-6 else (mid - mean_mid) / std_mid

        # Hybrid fair: stable wall anchor + EMA/imbalance signal + tiny z push.
        fair = 0.45 * wall_mid + 0.45 * fair_base + 0.10 * (mean_mid - z)

        # Adaptive taker gate by z-score confidence.
        take_width = 2 if abs(z) < 0.6 else 1 if abs(z) < 1.2 else 0
        pos, take_orders = self._take(od, fair, pos, take_width)
        orders.extend(take_orders)

        inv = pos / LIMIT
        half_spread = 2 if abs(z) < 1.0 else 3
        bid_px = math.floor(fair - half_spread - 2.8 * inv)
        ask_px = math.ceil(fair + half_spread - 2.8 * inv)

        if best_bid + 1 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 1 > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        base = 20
        buy_qty = min(buy_cap, max(0, int(base * (1 - inv))))
        sell_qty = min(sell_cap, max(0, int(base * (1 + inv))))

        # In reversion-stretched states, increase unwind side.
        if z > 1.3:
            sell_qty = min(sell_cap, sell_qty + 6)
            buy_qty = max(0, buy_qty - 6)
        elif z < -1.3:
            buy_qty = min(buy_cap, buy_qty + 6)
            sell_qty = max(0, sell_qty - 6)

        if abs(pos) >= 36:
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
