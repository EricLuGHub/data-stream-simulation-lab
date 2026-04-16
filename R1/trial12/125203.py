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

        wall_bid, wall_ask = self._get_walls(od, 11)
        wall_mid = 0.5 * (wall_bid + wall_ask)

        ema = 0.30 * mid + 0.70 * td.get("ema", mid)
        td["ema"] = ema

        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-30:]
        td["mid_hist"] = mids

        short = mids[-8:] if len(mids) >= 8 else mids
        long = mids[-20:] if len(mids) >= 20 else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        z = 0.0 if len(short) < 3 else (mid - short_mean) / max(1e-6, self._std(short))

        imb = self._imbalance(od)

        # Ensemble fair (three independent anchors + imbalance correction).
        fair = (
            0.40 * wall_mid +
            0.30 * ema +
            0.30 * (0.65 * short_mean + 0.35 * long_mean) +
            0.55 * imb
        )

        trend_bias = 1 if short_mean > long_mean else -1
        if abs(short_mean - long_mean) < 0.8:
            trend_bias = 0

        # Make take stricter during noisy/wide conditions.
        if spread <= 8:
            take_width = 0 if abs(z) > 1.0 else 1
            half_spread = 2
            base = 18
        elif spread <= 14:
            take_width = 1 if abs(z) > 0.9 else 2
            half_spread = 2
            base = 22
        else:
            take_width = 2
            half_spread = 3
            base = 26

        pos, take_orders = self._take(od, fair, pos, take_width)
        orders.extend(take_orders)

        inv = pos / LIMIT

        # Trend bias only nudges make prices; inventory control dominates.
        fair_adj = fair - 3.2 * inv + 0.4 * trend_bias

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

        # Extra defensive mode if inventory and z-score are aligned risk.
        if pos > 28 and z > 1.0:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 10)
        elif pos < -28 and z < -1.0:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 10)

        if abs(pos) >= 40:
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
