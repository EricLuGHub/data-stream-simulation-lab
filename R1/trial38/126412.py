from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 38: Robust adaptive-carry PEPPER model (submission-safe variant)."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, td)

        return result, 0, json.dumps(td)

    def _trade_pepper(self, state: TradingState, td: dict) -> List[Order]:
        od: OrderDepth = state.order_depths[PEPPER]
        if not od.buy_orders or not od.sell_orders:
            return []

        pos = state.position.get(PEPPER, 0)
        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        ts = state.timestamp

        prev_pos = td.get("prev_pos", pos)
        no_fill = td.get("no_fill", 0)
        if pos == prev_pos:
            no_fill = min(60, no_fill + 1)
        else:
            no_fill = 0
        td["prev_pos"] = pos
        td["no_fill"] = no_fill
        participation = min(1.0, no_fill / 24.0)

        heavy_bids = [p for p, v in od.buy_orders.items() if v >= 12]
        heavy_asks = [p for p, v in od.sell_orders.items() if -v >= 12]
        mm_bid = max(heavy_bids) if heavy_bids else best_bid
        mm_ask = min(heavy_asks) if heavy_asks else best_ask
        wall_mid = 0.5 * (mm_bid + mm_ask)

        ema = 0.30 * mid + 0.70 * td.get("ema", mid)
        td["ema"] = ema

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts
        drift = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        hist = td.get("mid_hist", [])
        hist.append(mid)
        hist = hist[-90:]
        td["mid_hist"] = hist

        short = hist[-8:] if len(hist) >= 8 else hist
        long = hist[-26:] if len(hist) >= 26 else hist
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        slope = short_mean - long_mean

        slope_hist = td.get("slope_hist", [])
        slope_hist.append(slope)
        slope_hist = slope_hist[-40:]
        td["slope_hist"] = slope_hist

        slope_mean = sum(slope_hist) / len(slope_hist)
        slope_std = self._std(slope_hist)

        fair = 0.46 * wall_mid + 0.30 * drift + 0.24 * ema

        resid = mid - fair
        r_hist = td.get("r_hist", [])
        r_hist.append(resid)
        r_hist = r_hist[-120:]
        td["r_hist"] = r_hist
        z = resid / max(0.85, self._std(r_hist))

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        bucket = min(9, int(progress * 10))

        # Base carry path from trial33.
        target_by_bucket = [46.0, 46.0, 45.0, 43.0, 40.0, 36.0, 33.0, 31.0, 30.0, 30.0]
        target = target_by_bucket[bucket]

        # Adaptive late carry boost: only if trend evidence is stable and positive.
        strong_up = slope_mean > 0.85 and slope_std < 1.0
        weak_or_choppy = slope_mean < 0.35 or slope_std > 1.5
        if bucket >= 7 and strong_up:
            target += [0.0, 12.0, 14.0, 16.0][bucket - 6]
        elif bucket >= 7 and weak_or_choppy:
            target -= [0.0, 3.0, 5.0, 6.0][bucket - 6]

        if slope > 1.0:
            target += 4.0
        elif slope < -0.8:
            target -= 6.0
        if z <= -1.1:
            target += 4.0
        if z >= 2.6:
            target -= 6.0
        target = max(2.0, min(49.0, target))

        orders: List[Order] = []

        take_edge = 1 + (1 if participation > 0.45 else 0)
        take_cap = 7 + int(4 * participation)
        if slope >= -0.2 or z <= -0.8:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + take_edge:
                    qty = min(-ask_vol, LIMIT - pos, take_cap)
                    if qty > 0:
                        orders.append(Order(PEPPER, ask_px, qty))
                        pos += qty

        # Faster de-risk in weak/choppy late phase to avoid submission-day collapses.
        late_weak = bucket >= 7 and weak_or_choppy
        if (z >= (2.5 if late_weak else 2.9) and pos > target + 3) or (slope < (-0.3 if late_weak else -0.5) and pos > target + 7):
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 1:
                    qty = min(bid_vol, LIMIT + pos, 8)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        spread = 2 if slope >= 0 else 3
        spread = max(1, spread - (1 if participation > 0.55 else 0))

        bid_px = math.floor(fair - spread - 1.9 * inv_ratio + 0.15 * slope)
        ask_px = math.ceil(fair + spread - 1.9 * inv_ratio + 0.15 * slope)

        if participation > 0.65 and best_ask - best_bid <= 3:
            bid_px = max(bid_px, best_bid)
            ask_px = min(ask_px, best_ask)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_base = 24 + int(9 * participation)
        sell_base = 14 + int(4 * participation)

        buy_qty = min(buy_cap, max(1, int(buy_base * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(sell_base * (1 + inv_ratio))))

        suppress_sell = (slope > 0.7 and pos < target - 4) or (z <= -1.2)
        suppress_buy = (slope < -1.1 and pos > target + 8 and z > 0.2)

        if buy_qty > 0 and not suppress_buy:
            orders.append(Order(PEPPER, bid_px, buy_qty))
        if sell_qty > 0 and not suppress_sell:
            orders.append(Order(PEPPER, ask_px, -sell_qty))

        return self._clamp(orders, state.position.get(PEPPER, 0), LIMIT)

    def _load_td(self, raw: str):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _std(self, xs: List[float]) -> float:
        if len(xs) < 2:
            return 1.0
        m = sum(xs) / len(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

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
