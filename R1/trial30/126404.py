from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 30: Time-profiled trend carry with residual pullback entries."""

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

        # Filter out tiny volume levels when estimating passive fair value.
        heavy_bids = [p for p, v in od.buy_orders.items() if v >= 10]
        heavy_asks = [p for p, v in od.sell_orders.items() if -v >= 10]
        wall_bid = max(heavy_bids) if heavy_bids else best_bid
        wall_ask = min(heavy_asks) if heavy_asks else best_ask
        wall_mid = 0.5 * (wall_bid + wall_ask)

        ema_fast = 0.35 * mid + 0.65 * td.get("ema_fast", mid)
        ema_slow = 0.08 * mid + 0.92 * td.get("ema_slow", mid)
        td["ema_fast"] = ema_fast
        td["ema_slow"] = ema_slow

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts
        drift = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        fair = 0.48 * wall_mid + 0.30 * ema_fast + 0.22 * drift

        resid = mid - fair
        r_hist = td.get("r_hist", [])
        r_hist.append(resid)
        r_hist = r_hist[-120:]
        td["r_hist"] = r_hist
        r_std = max(0.8, self._std(r_hist))
        z = resid / r_std

        slope = ema_fast - ema_slow
        progress = min(max(ts / 99900.0, 0.0), 1.0)
        bucket = min(9, int(progress * 10))

        # Intraday target profile: keep meaningful long carry throughout,
        # but avoid getting trapped with excessive stale inventory late.
        target_path = [46.0, 45.0, 44.0, 42.0, 39.0, 35.0, 32.0, 28.0, 24.0, 20.0]
        target = target_path[bucket]
        if slope > 1.4:
            target += 4.0
        elif slope < -0.6:
            target -= 5.0

        if z <= -1.2:
            target += 5.0
        if z >= 2.4:
            target -= 8.0
        target = max(2.0, min(48.0, target))

        orders: List[Order] = []

        # Aggressive dip-taking is strongest early/mid where prior logs were best.
        take_cap = 10 if bucket <= 4 else (8 if bucket <= 7 else 6)
        take_edge = 2 if bucket <= 5 else 1
        if z <= 0.9:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + take_edge:
                    qty = min(-ask_vol, LIMIT - pos, take_cap)
                    if qty > 0:
                        orders.append(Order(PEPPER, ask_px, qty))
                        pos += qty

        # Scale out only on stretched upside or clear trend deterioration.
        if (z >= 2.6 and pos > target + 4) or (slope < -0.3 and pos > target + 8):
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 1:
                    qty = min(bid_vol, LIMIT + pos, 8)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        base_spread = 2 if slope >= 0 else 3
        skew = 1.9 if bucket <= 6 else 2.3

        bid_px = math.floor(fair - base_spread - skew * inv_ratio)
        ask_px = math.ceil(fair + base_spread - skew * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_base = 30 if bucket <= 4 else (26 if bucket <= 7 else 20)
        sell_base = 14 if bucket <= 4 else (18 if bucket <= 7 else 22)

        buy_qty = min(buy_cap, max(1, int(buy_base * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(sell_base * (1 + inv_ratio))))

        suppress_sell = (slope > 0.8 and pos < target - 3) or (z <= -1.3)
        suppress_buy = (slope < -0.8 and pos > target + 8 and z > 0.5)

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
