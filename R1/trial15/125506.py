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
        mids = mids[-40:]
        td["mid_hist"] = mids

        ema_slow = 0.18 * mid + 0.82 * td.get("ema_slow", mid)
        td["ema_slow"] = ema_slow

        wall_bid, wall_ask = self._get_walls(od, min_wall_volume=12)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        look = mids[-14:] if len(mids) >= 14 else mids
        short_mean = sum(look) / len(look)
        short_std = self._std(look)
        z = 0.0 if short_std <= 1e-6 else (mid - short_mean) / short_std

        # Conservative fair anchor favors stable components over fast moves.
        fair = 0.50 * wall_mid + 0.35 * ema_slow + 0.15 * short_mean + 0.35 * imb

        inv = pos / LIMIT

        # Only take when both edge and inventory pressure agree.
        if pos > 22:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair - 0.5:
                    qty = min(bid_vol, pos - 18)
                    if qty > 0:
                        orders.append(Order(ASH, bid_px, -qty))
                        pos -= qty
        elif pos < -22:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + 0.5:
                    qty = min(-ask_vol, -pos - 18)
                    if qty > 0:
                        orders.append(Order(ASH, ask_px, qty))
                        pos += qty

        # Passive quote placement with larger width in noisy states.
        if spread <= 10 and abs(z) < 1.0:
            half_spread = 2
            base_size = 14
        elif spread <= 16:
            half_spread = 3
            base_size = 12
        else:
            half_spread = 4
            base_size = 10

        fair_adj = fair - 4.0 * (pos / LIMIT)
        bid_quote = math.floor(fair_adj - half_spread)
        ask_quote = math.ceil(fair_adj + half_spread)

        if best_bid + 2 < fair_adj:
            bid_quote = max(bid_quote, best_bid + 1)
        if best_ask - 2 > fair_adj:
            ask_quote = min(ask_quote, best_ask - 1)

        if bid_quote >= ask_quote:
            bid_quote = ask_quote - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_qty = min(buy_cap, max(0, int(base_size * (1 - 0.8 * (pos / LIMIT)))))
        sell_qty = min(sell_cap, max(0, int(base_size * (1 + 0.8 * (pos / LIMIT)))))

        if pos >= 30 or z > 1.7:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 6)
        elif pos <= -30 or z < -1.7:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 6)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_quote, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_quote, -sell_qty))

        result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
        return result, 0, json.dumps(td)

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
