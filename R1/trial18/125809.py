from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"

LIMITS = {
    ASH: 50,
    PEPPER: 50,
}


class Trader:
    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if ASH in state.order_depths:
            result[ASH] = self._trade_ash(state, td)

        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, td)

        return result, 0, json.dumps(td)

    # ------------------------ ASH (trial14 logic) ------------------------

    def _trade_ash(self, state: TradingState, td: dict) -> List[Order]:
        od = state.order_depths[ASH]
        pos = state.position.get(ASH, 0)

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None or best_ask is None:
            return []

        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid

        ema = 0.20 * mid + 0.80 * td.get("ash_ema", mid)
        td["ash_ema"] = ema

        mids = td.get("ash_mid_hist", [])
        mids.append(mid)
        mids = mids[-35:]
        td["ash_mid_hist"] = mids

        short = mids[-10:] if len(mids) >= 10 else mids
        long = mids[-24:] if len(mids) >= 24 else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

        wall_bid, wall_ask = self._get_walls(od, 12)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        fair = 0.55 * wall_mid + 0.25 * ema + 0.20 * (0.6 * short_mean + 0.4 * long_mean) + 0.45 * imb

        take_width = 1 if abs(z) < 1.0 else 0
        pos, orders = self._take_with_cap(ASH, od, fair, pos, LIMITS[ASH], take_width, 4)

        inv = pos / LIMITS[ASH]
        half_spread = 3 if spread <= 12 else 4
        bid_px = math.floor(fair - half_spread - 3.8 * inv)
        ask_px = math.ceil(fair + half_spread - 3.8 * inv)

        if best_bid + 2 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 2 > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMITS[ASH] - pos)
        sell_cap = max(0, LIMITS[ASH] + pos)

        base = 14
        buy_qty = min(buy_cap, max(0, int(base * (1 - 0.7 * inv))))
        sell_qty = min(sell_cap, max(0, int(base * (1 + 0.7 * inv))))

        if pos > 35 or z > 1.8:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 6)
        elif pos < -35 or z < -1.8:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 6)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        return self._clamp(orders, state.position.get(ASH, 0), LIMITS[ASH])

    # --------------------- PEPPER (trend-capture logic) ---------------------

    def _trade_pepper(self, state: TradingState, td: dict) -> List[Order]:
        od = state.order_depths[PEPPER]
        pos = state.position.get(PEPPER, 0)

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None or best_ask is None:
            return []

        timestamp = state.timestamp
        mid = 0.5 * (best_bid + best_ask)

        anchor_price_key = "pepper_anchor_price"
        anchor_ts_key = "pepper_anchor_ts"
        ema_key = "pepper_ema"

        if anchor_price_key not in td:
            td[anchor_price_key] = mid
            td[anchor_ts_key] = timestamp

        anchor_price = td.get(anchor_price_key, mid)
        anchor_ts = td.get(anchor_ts_key, timestamp)
        elapsed = timestamp - anchor_ts

        trend_slope = 0.001
        trend_est = anchor_price + trend_slope * elapsed

        ema = 0.30 * mid + 0.70 * td.get(ema_key, mid)
        td[ema_key] = ema

        trend_weight = 0.50
        base_fair = trend_weight * trend_est + (1 - trend_weight) * ema

        max_ts = 999900
        remaining = max(0.0, 1.0 - timestamp / max_ts)
        trend_edge = 5.0 * remaining
        fair = base_fair + trend_edge

        take_width = 0
        pos, orders = self._take_with_cap(PEPPER, od, fair, pos, LIMITS[PEPPER], take_width, 8)

        target_start = 40.0
        target_end = 0.0
        progress = min(timestamp / max_ts, 1.0)
        target_pos = target_start + (target_end - target_start) * progress

        deviation = pos - target_pos
        ratio = deviation / LIMITS[PEPPER]

        half_spread = 2
        skew = 2.0
        fair_adj = fair - ratio * skew

        bid_px = math.floor(fair_adj - half_spread)
        ask_px = math.ceil(fair_adj + half_spread)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMITS[PEPPER] - pos)
        sell_cap = max(0, LIMITS[PEPPER] + pos)
        base_size = 35

        buy_qty = min(buy_cap, max(1, int(base_size * (1 - ratio))))
        sell_qty = min(sell_cap, max(1, int(base_size * (1 + ratio))))

        # Suppress the wrong side if we are far from trend target.
        gap_threshold = 5
        suppress_sell = deviation < -gap_threshold
        suppress_buy = deviation > gap_threshold

        if buy_qty > 0 and not suppress_buy:
            orders.append(Order(PEPPER, bid_px, buy_qty))
        if sell_qty > 0 and not suppress_sell:
            orders.append(Order(PEPPER, ask_px, -sell_qty))

        return self._clamp(orders, state.position.get(PEPPER, 0), LIMITS[PEPPER])

    # ------------------------------- helpers -------------------------------

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

    def _take_with_cap(self, product: str, od: OrderDepth, fair: float, pos: int, limit: int, width: int, cap: int):
        orders: List[Order] = []
        for ask_px, ask_vol in sorted(od.sell_orders.items()):
            if ask_px <= fair - width:
                qty = min(-ask_vol, limit - pos, cap)
                if qty > 0:
                    orders.append(Order(product, ask_px, qty))
                    pos += qty

        for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
            if bid_px >= fair + width:
                qty = min(bid_vol, limit + pos, cap)
                if qty > 0:
                    orders.append(Order(product, bid_px, -qty))
                    pos -= qty

        return pos, orders

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
