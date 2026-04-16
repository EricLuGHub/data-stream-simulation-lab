from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 21: PEPPER hybrid trend-anchor plus residual z-gating."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, td)

        return result, 0, json.dumps(td)

    def _trade_pepper(self, state: TradingState, td: dict) -> List[Order]:
        od: OrderDepth = state.order_depths[PEPPER]
        pos = state.position.get(PEPPER, 0)

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None or best_ask is None:
            return []

        ts = state.timestamp
        mid = 0.5 * (best_bid + best_ask)

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts

        trend = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])
        ema = 0.32 * mid + 0.68 * td.get("ema", mid)
        td["ema"] = ema

        fair = 0.55 * trend + 0.45 * ema
        resid = mid - fair

        hist = td.get("res_hist", [])
        hist.append(resid)
        hist = hist[-120:]
        td["res_hist"] = hist
        sigma = self._std(hist)
        if sigma < 0.9:
            sigma = 0.9
        z = resid / sigma

        orders: List[Order] = []

        # Buy residual pullbacks; avoid extension chasing.
        if z <= -1.4 and od.sell_orders:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + 1:
                    qty = min(-ask_vol, LIMIT - pos, 7)
                    if qty > 0:
                        orders.append(Order(PEPPER, ask_px, qty))
                        pos += qty

        # Small profit-taking only at strong positive extension.
        if z >= 2.6 and od.buy_orders:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair - 1:
                    qty = min(bid_vol, LIMIT + pos, 6)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        # Dynamic target from z-buckets: deeper pullback -> bigger long target.
        if z <= -2.0:
            target = 42
        elif z <= -1.0:
            target = 34
        elif z < 1.8:
            target = 24
        else:
            target = 10

        inv_ratio = (pos - target) / LIMIT
        spread = 2 if abs(z) < 2.5 else 3

        bid_px = math.floor(fair - spread - 2.0 * inv_ratio)
        ask_px = math.ceil(fair + spread - 2.0 * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)
        buy_qty = min(buy_cap, max(1, int(15 * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(11 * (1 + inv_ratio))))

        if z <= -1.5:
            sell_qty = max(0, sell_qty - 5)
        if z >= 2.4:
            buy_qty = max(0, buy_qty - 8)

        if buy_qty > 0:
            orders.append(Order(PEPPER, bid_px, buy_qty))
        if sell_qty > 0:
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
