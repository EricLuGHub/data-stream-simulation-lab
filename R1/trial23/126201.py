from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 23: Wall-mid trend gating (inspired by top-team filtered fair-value MM)."""

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

        filt_bids = [p for p, v in od.buy_orders.items() if abs(v) >= 10]
        filt_asks = [p for p, v in od.sell_orders.items() if abs(v) >= 10]
        mm_bid = max(filt_bids) if filt_bids else best_bid
        mm_ask = min(filt_asks) if filt_asks else best_ask
        wall_mid = 0.5 * (mm_bid + mm_ask)

        hist = td.get("mid_hist", [])
        hist.append(mid)
        hist = hist[-80:]
        td["mid_hist"] = hist

        short = hist[-8:] if len(hist) >= 8 else hist
        long = hist[-28:] if len(hist) >= 28 else hist
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)

        trend = 0
        if short_mean > long_mean + 0.6:
            trend = 1
        elif short_mean < long_mean - 0.6:
            trend = -1

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts
        drift = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        fair = 0.55 * wall_mid + 0.25 * short_mean + 0.20 * drift

        resid = mid - fair
        r_hist = td.get("resid_hist", [])
        r_hist.append(resid)
        r_hist = r_hist[-100:]
        td["resid_hist"] = r_hist
        r_std = self._std(r_hist)
        if r_std < 0.8:
            r_std = 0.8
        z = resid / r_std

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        base_target = 44.0 + (18.0 - 44.0) * progress

        target = base_target + (6 if trend > 0 else (-8 if trend < 0 else 0))
        if z <= -1.2:
            target += 5
        if z >= 2.4:
            target -= 8
        target = max(4.0, min(48.0, target))

        orders: List[Order] = []

        buy_take_cap = 10 if (trend > 0 or z <= -1.0) else 6
        for ask_px, ask_vol in sorted(od.sell_orders.items()):
            if ask_px <= fair + 1:
                qty = min(-ask_vol, LIMIT - pos, buy_take_cap)
                if qty > 0:
                    orders.append(Order(PEPPER, ask_px, qty))
                    pos += qty

        if z >= 2.8 and pos > target + 3:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 1:
                    qty = min(bid_vol, LIMIT + pos, 7)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        spread = 2 if trend >= 0 else 3
        bid_px = math.floor(fair - spread - 2.0 * inv_ratio)
        ask_px = math.ceil(fair + spread - 2.0 * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_qty = min(buy_cap, max(1, int(30 * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(18 * (1 + inv_ratio))))

        suppress_sell = (trend > 0 and pos < target - 2) or (z <= -1.4)
        suppress_buy = (trend < 0 and pos > target + 8)

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
