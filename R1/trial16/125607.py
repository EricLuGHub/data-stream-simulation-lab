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

        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-48:]
        td["mid_hist"] = mids

        short = mids[-8:] if len(mids) >= 8 else mids
        long = mids[-26:] if len(mids) >= 26 else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        short_std = self._std(short)
        z = 0.0 if short_std <= 1e-6 else (mid - short_mean) / short_std

        ema_fast = 0.42 * mid + 0.58 * td.get("ema_fast", mid)
        td["ema_fast"] = ema_fast

        wall_bid, wall_ask = self._get_walls(od, min_wall_volume=10)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        trend_strength = short_mean - long_mean
        mode = "trend" if abs(trend_strength) >= 1.2 and abs(z) <= 1.6 else "revert"
        td["mode"] = mode

        if mode == "trend":
            fair = 0.30 * wall_mid + 0.55 * ema_fast + 0.15 * short_mean + 0.55 * imb
            half_spread = 2 if spread <= 12 else 3
            take_width = 1
            base_size = 18
        else:
            fair = 0.50 * wall_mid + 0.25 * ema_fast + 0.25 * long_mean + 0.40 * imb
            half_spread = 3 if spread <= 12 else 4
            take_width = 0
            base_size = 12

        # Distinct from trial15: this strategy adapts between trend and reversion states.
        pos, take_orders = self._take_layer(od, fair, pos, take_width, mode)
        orders.extend(take_orders)

        inv = pos / LIMIT
        fair_adj = fair - 3.0 * inv
        bid_quote = math.floor(fair_adj - half_spread)
        ask_quote = math.ceil(fair_adj + half_spread)

        if best_bid + 1 < fair_adj:
            bid_quote = max(bid_quote, best_bid + 1)
        if best_ask - 1 > fair_adj:
            ask_quote = min(ask_quote, best_ask - 1)
        if bid_quote >= ask_quote:
            bid_quote = ask_quote - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        if mode == "trend":
            direction = 1 if trend_strength > 0 else -1
            buy_qty = min(buy_cap, max(0, int(base_size * (1 - inv))))
            sell_qty = min(sell_cap, max(0, int(base_size * (1 + inv))))
            if direction > 0:
                buy_qty = min(buy_cap, buy_qty + 4)
                sell_qty = max(0, sell_qty - 4)
            else:
                sell_qty = min(sell_cap, sell_qty + 4)
                buy_qty = max(0, buy_qty - 4)
        else:
            buy_qty = min(buy_cap, max(0, int(base_size * (1 - 0.9 * inv))))
            sell_qty = min(sell_cap, max(0, int(base_size * (1 + 0.9 * inv))))
            if z > 1.3:
                buy_qty = 0
                sell_qty = min(sell_cap, sell_qty + 5)
            elif z < -1.3:
                sell_qty = 0
                buy_qty = min(buy_cap, buy_qty + 5)

        if abs(pos) >= 34:
            if pos > 0:
                buy_qty = 0
                sell_qty = min(sell_cap, sell_qty + 8)
            else:
                sell_qty = 0
                buy_qty = min(buy_cap, buy_qty + 8)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_quote, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_quote, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(td)

    def _take_layer(self, od: OrderDepth, fair: float, pos: int, width: int, mode: str):
        orders: List[Order] = []
        take_cap = 6 if mode == "trend" else 4

        for ask_px, ask_vol in sorted(od.sell_orders.items()):
            if ask_px <= fair - width:
                qty = min(-ask_vol, LIMIT - pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, ask_px, qty))
                    pos += qty

        for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
            if bid_px >= fair + width:
                qty = min(bid_vol, LIMIT + pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, bid_px, -qty))
                    pos -= qty

        return pos, orders

    def _load_td(self, raw: str):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _std(self, xs: List[float]) -> float:
        if not xs:
            return 0.0
        m = sum(xs) / len(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

    def _imbalance(self, od: OrderDepth) -> float:
        bid = sum(od.buy_orders.values())
        ask = sum(-v for v in od.sell_orders.values())
        den = bid + ask
        return 0.0 if den == 0 else (bid - ask) / den

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
