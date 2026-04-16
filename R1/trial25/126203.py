from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 25: Phase-switch carry model (early dominance + late momentum capture)."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}
        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, td)
        return result, 0, json.dumps(td)

    def _trade_pepper(self, state: TradingState, td: dict) -> List[Order]:
        od = state.order_depths[PEPPER]
        pos = state.position.get(PEPPER, 0)
        if not od.buy_orders or not od.sell_orders:
            return []

        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        ts = state.timestamp

        ema_fast = 0.42 * mid + 0.58 * td.get("ema_fast", mid)
        ema_slow = 0.10 * mid + 0.90 * td.get("ema_slow", mid)
        td["ema_fast"] = ema_fast
        td["ema_slow"] = ema_slow

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts
        trend = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        fair = 0.58 * trend + 0.42 * ema_fast
        slope = ema_fast - ema_slow

        r = mid - fair
        r_hist = td.get("r_hist", [])
        r_hist.append(r)
        r_hist = r_hist[-120:]
        td["r_hist"] = r_hist
        r_std = self._std(r_hist)
        if r_std < 0.8:
            r_std = 0.8
        z = r / r_std

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        early_phase = progress < 0.75

        if early_phase:
            target = 46.0 + (30.0 - 46.0) * (progress / 0.75)
            if slope > 1.0:
                target += 3.0
            if z <= -1.0:
                target += 4.0
            if z >= 2.2:
                target -= 7.0
            base_buy = 34
            base_sell = 16
        else:
            # Late phase: reduce stale inventory risk while still monetizing momentum.
            target = 24.0 + (10.0 - 24.0) * ((progress - 0.75) / 0.25)
            if slope > 1.5:
                target += 8.0
            if slope < -0.2:
                target -= 8.0
            if z <= -1.4:
                target += 5.0
            base_buy = 24
            base_sell = 22

        target = max(3.0, min(49.0, target))

        orders: List[Order] = []

        # Taker logic: early accumulate aggressively, late only when edge is strong.
        buy_edge = 2 if early_phase else (2 if slope > 1.6 else 1)
        buy_take_cap = 10 if early_phase else 7

        for ask_px, ask_vol in sorted(od.sell_orders.items()):
            if ask_px <= fair + buy_edge:
                qty = min(-ask_vol, LIMIT - pos, buy_take_cap)
                if qty > 0:
                    orders.append(Order(PEPPER, ask_px, qty))
                    pos += qty

        if (z >= 2.8 and pos > target + 4) or (not early_phase and slope < -0.5 and pos > target):
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 1:
                    qty = min(bid_vol, LIMIT + pos, 8)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        spread = 2 if early_phase else 3
        skew = 2.0 if early_phase else 2.4

        bid_px = math.floor(fair - spread - skew * inv_ratio)
        ask_px = math.ceil(fair + spread - skew * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_qty = min(buy_cap, max(1, int(base_buy * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(base_sell * (1 + inv_ratio))))

        suppress_sell = early_phase and (pos < target - 3 or z <= -1.3)
        suppress_buy = (not early_phase) and slope < -0.7 and pos > target + 6

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
