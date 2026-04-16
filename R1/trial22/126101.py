from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 22: PEPPER long-carry hybrid with momentum and pullback adaptation."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, td)

        return result, 0, json.dumps(td)

    def _trade_pepper(self, state: TradingState, td: dict) -> List[Order]:
        od: OrderDepth = state.order_depths[PEPPER]
        pos = state.position.get(PEPPER, 0)

        if not od.buy_orders or not od.sell_orders:
            return []

        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        mid = 0.5 * (best_bid + best_ask)
        ts = state.timestamp

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts

        trend = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        ema = 0.28 * mid + 0.72 * td.get("ema", mid)
        ema_fast = 0.45 * mid + 0.55 * td.get("ema_fast", mid)
        ema_slow = 0.08 * mid + 0.92 * td.get("ema_slow", mid)
        td["ema"] = ema
        td["ema_fast"] = ema_fast
        td["ema_slow"] = ema_slow

        # Keep explicit drift edge because PEPPER is strongly upward in this round.
        fair = 0.62 * trend + 0.38 * ema
        slope_signal = ema_fast - ema_slow

        resid = mid - fair
        resid_hist = td.get("resid_hist", [])
        resid_hist.append(resid)
        resid_hist = resid_hist[-120:]
        td["resid_hist"] = resid_hist

        resid_std = self._std(resid_hist)
        if resid_std < 0.8:
            resid_std = 0.8
        z = resid / resid_std

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        base_target = 44.0 + (24.0 - 44.0) * progress

        target = base_target
        if progress < 0.5:
            target += 6.0
        if slope_signal > 1.2:
            target += 4.0
        if z <= -1.0:
            target += 6.0
        if z >= 2.2:
            target -= 8.0

        target = max(6.0, min(48.0, target))

        orders: List[Order] = []

        # Pullback and continuation taker buys, capped to avoid blowups.
        buy_take_cap = 10 if z <= -1.0 else 7
        buy_take_edge = 2 if (z <= -1.0 or slope_signal > 1.8) else 1

        for ask_px, ask_vol in sorted(od.sell_orders.items()):
            if ask_px <= fair + buy_take_edge:
                qty = min(-ask_vol, LIMIT - pos, buy_take_cap)
                if qty > 0:
                    orders.append(Order(PEPPER, ask_px, qty))
                    pos += qty

        # Sell taker only when very extended or clearly above target.
        can_take_sell = (z >= 2.8) or (pos > target + 6)
        if can_take_sell:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 2:
                    qty = min(bid_vol, LIMIT + pos, 7)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        half_spread = 2 if progress < 0.75 else 3
        skew = 2.1

        bid_px = math.floor(fair - half_spread - skew * inv_ratio)
        ask_px = math.ceil(fair + half_spread - skew * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        base_buy = 32 if progress < 0.6 else 26
        base_sell = 18 if progress < 0.6 else 22

        buy_qty = min(buy_cap, max(1, int(base_buy * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(base_sell * (1 + inv_ratio))))

        # Keep long carry by suppressing sells when under target.
        suppress_sell = pos < (target - 3)
        suppress_buy = pos > (target + 9)

        if z <= -1.3:
            sell_qty = max(0, sell_qty - 8)
        if z >= 2.6:
            buy_qty = max(0, buy_qty - 10)

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
