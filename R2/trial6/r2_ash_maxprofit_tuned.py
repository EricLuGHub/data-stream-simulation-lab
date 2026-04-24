from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
    """R2 Trial 6: ASH profit-max variant tuned on days -1 and 0."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if ASH not in state.order_depths:
            return result, 0, json.dumps(td)

        od = state.order_depths[ASH]
        if not od.buy_orders or not od.sell_orders:
            result[ASH] = []
            return result, 0, json.dumps(td)

        pos = state.position.get(ASH, 0)
        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid
        ts = state.timestamp

        prev_pos = td.get("prev_pos", pos)
        no_fill = td.get("no_fill", 0)
        if pos == prev_pos:
            no_fill = min(80, no_fill + 1)
        else:
            no_fill = 0
        td["prev_pos"] = pos
        td["no_fill"] = no_fill
        participation = min(1.0, no_fill / 20.0)

        ema = 0.26 * mid + (1.0 - 0.26) * td.get("ema", mid)
        td["ema"] = ema

        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-52:]
        td["mid_hist"] = mids

        short = mids[-10:] if len(mids) >= 10 else mids
        long = mids[-26:] if len(mids) >= 26 else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        slope = short_mean - long_mean
        z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

        wall_bid, wall_ask = self._get_walls(od, 11)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        fair = 0.52 * wall_mid + 0.28 * ema + 0.2 * (0.6 * short_mean + 0.4 * long_mean) + 0.5 * imb

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        bucket = min(9, int(progress * 10))
        target_by_bucket = [36.0, 36.0, 35.0, 34.0, 32.0, 31.0, 31.0, 37.0, 40.0, 41.0]
        target = target_by_bucket[bucket]
        if slope > 0.8:
            target += 4.0
        elif slope < -0.7:
            target -= 2.0
        if z <= -1.2:
            target += 4.0
        if z >= 1.8:
            target -= 3.0
        target = max(-48.0, min(48.0, target))

        orders: List[Order] = []

        take_width = 1
        if abs(z) >= 1.3:
            take_width = 0
        take_cap = 6 + int(4 * participation)

        for ask, vol in sorted(od.sell_orders.items()):
            if ask <= fair - take_width:
                qty = min(-vol, LIMIT - pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, ask, qty))
                    pos += qty

        carry_floor = 0
        if progress >= 0.42 and slope > 0.45:
            carry_floor = 32
        if progress >= 0.7 and slope > 0.65:
            carry_floor = max(carry_floor, 42)

        if (z >= 2.4 and pos > target + 6) or (slope < -0.55 and pos > target + (6 + 2)):
            for bid, vol in sorted(od.buy_orders.items(), reverse=True):
                if bid >= fair + 1:
                    qty = min(vol, LIMIT + pos, 8)
                    qty = min(qty, max(0, pos - carry_floor))
                    if qty > 0:
                        orders.append(Order(ASH, bid, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT

        base_half = 2 if spread <= 12 else 3
        if participation > 0.6:
            base_half = max(1, base_half - 1)

        bid_px = math.floor(fair - base_half - 4.6 * inv_ratio + 0.2 * slope)
        ask_px = math.ceil(fair + base_half - 4.6 * inv_ratio + 0.2 * slope)

        if best_bid + 1 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 1 > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_base = 26 + int(8 * participation)
        sell_base = 21 + int(4 * participation)
        buy_qty = min(buy_cap, max(1, int(buy_base * (1 - 1.0 * inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(sell_base * (1 + 1.0 * inv_ratio))))

        suppress_sell = (slope > 0.65 and pos < target + 2) or (z <= -0.65) or (pos <= carry_floor)
        suppress_buy = (slope < -1.0 and pos > target + 8 and z > 0.2)

        if buy_qty > 0 and not suppress_buy:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0 and not suppress_sell:
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

    def _std(self, xs: List[float]):
        if len(xs) < 2:
            return 1.0
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
