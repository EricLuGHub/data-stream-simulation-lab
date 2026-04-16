from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 20: PEPPER momentum continuation with trailing exits."""

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

        mid = 0.5 * (best_bid + best_ask)

        ema_fast = 0.40 * mid + 0.60 * td.get("ema_fast", mid)
        ema_slow = 0.08 * mid + 0.92 * td.get("ema_slow", mid)
        td["ema_fast"] = ema_fast
        td["ema_slow"] = ema_slow

        slope = ema_fast - ema_slow
        up_regime = slope > 1.2
        down_regime = slope < -0.8

        fair = 0.75 * ema_fast + 0.25 * ema_slow

        orders: List[Order] = []

        # Breakout taker in strong up regime.
        if up_regime and od.sell_orders:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + 2:
                    qty = min(-ask_vol, LIMIT - pos, 9)
                    if qty > 0:
                        orders.append(Order(PEPPER, ask_px, qty))
                        pos += qty

        # Trailing de-risk once momentum weakens.
        if (down_regime or slope < 0.2) and pos > 0 and od.buy_orders:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair - 3:
                    qty = min(bid_vol, LIMIT + pos, 8)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        target = 34 if up_regime else 14
        if down_regime:
            target = 2

        inv_ratio = (pos - target) / LIMIT
        bid_px = math.floor(fair - 2 - 2.2 * inv_ratio)
        ask_px = math.ceil(fair + 2 - 2.2 * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)
        buy_qty = min(buy_cap, max(1, int(16 * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(14 * (1 + inv_ratio))))

        if up_regime:
            sell_qty = max(0, sell_qty - 6)
        if down_regime:
            buy_qty = max(0, buy_qty - 10)

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
