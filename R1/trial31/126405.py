from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 31: Regime-persistence pullback engine with quick de-risk."""

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

        ema_fast = 0.32 * mid + 0.68 * td.get("ema_fast", mid)
        ema_slow = 0.10 * mid + 0.90 * td.get("ema_slow", mid)
        td["ema_fast"] = ema_fast
        td["ema_slow"] = ema_slow
        slope = ema_fast - ema_slow

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts
        drift = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        best_bid_vol = max(0, od.buy_orders.get(best_bid, 0))
        best_ask_vol = max(0, -od.sell_orders.get(best_ask, 0))
        micro = mid
        if best_bid_vol + best_ask_vol > 0:
            micro = (best_ask * best_bid_vol + best_bid * best_ask_vol) / (best_bid_vol + best_ask_vol)

        fair = 0.46 * ema_fast + 0.34 * drift + 0.20 * micro

        resid = mid - fair
        r_hist = td.get("r_hist", [])
        r_hist.append(resid)
        r_hist = r_hist[-140:]
        td["r_hist"] = r_hist
        z = resid / max(0.9, self._std(r_hist))

        # Track short persistence runs (1-4 ticks are dominant in your diagnostics).
        prev_sign = td.get("prev_sign", 0)
        sign = -1 if z < 0 else 1
        run_len = td.get("run_len", 0)
        if sign == prev_sign:
            run_len += 1
        else:
            run_len = 1
        td["prev_sign"] = sign
        td["run_len"] = min(20, run_len)

        below_persist = sign < 0 and 2 <= run_len <= 6
        above_persist = sign > 0 and 2 <= run_len <= 6

        progress = min(max(ts / 99900.0, 0.0), 1.0)

        # Keep positive carry baseline, then modulate by regime persistence.
        base_target = 38.0 + (18.0 - 38.0) * progress
        target = base_target
        if below_persist and slope >= -0.2:
            target += 8.0
        if above_persist and z > 1.2:
            target -= 6.0
        if slope > 1.2:
            target += 4.0
        if slope < -0.8:
            target -= 7.0
        target = max(2.0, min(47.0, target))

        orders: List[Order] = []

        # Enter primarily on persistent pullbacks, not on random one-tick noise.
        if below_persist or z <= -1.4:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + 1:
                    cap = 9 if run_len <= 4 else 7
                    qty = min(-ask_vol, LIMIT - pos, cap)
                    if qty > 0:
                        orders.append(Order(PEPPER, ask_px, qty))
                        pos += qty

        # De-risk into persistent overextension.
        if above_persist and z >= 1.8 and pos > target:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair:
                    qty = min(bid_vol, LIMIT + pos, 8)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        spread = 2 if slope >= 0 else 3
        skew = 2.1

        bid_px = math.floor(fair - spread - skew * inv_ratio)
        ask_px = math.ceil(fair + spread - skew * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_base = 26
        sell_base = 18
        buy_qty = min(buy_cap, max(1, int(buy_base * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(sell_base * (1 + inv_ratio))))

        suppress_sell = (slope > 0.7 and pos < target - 2) or (z <= -1.5)
        suppress_buy = slope < -1.0 and pos > target + 8 and z > 0.0

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
