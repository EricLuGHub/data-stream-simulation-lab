from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Trial 24: Vol-spike mean reversion with position timeout and trend filter."""

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

        prices = td.get("prices", [])
        prices.append(mid)
        prices = prices[-120:]
        td["prices"] = prices

        if len(prices) < 12:
            fair = mid
            short_mean = long_mean = mid
        else:
            short = prices[-10:]
            long = prices[-40:] if len(prices) >= 40 else prices
            short_mean = sum(short) / len(short)
            long_mean = sum(long) / len(long)
            fair = 0.65 * short_mean + 0.35 * long_mean

        vol = self._std(prices[-12:]) if len(prices) >= 12 else 0.0
        vol_thr = 2.5
        deviation = mid - fair

        trend_up = short_mean >= long_mean

        entry_ts = td.get("entry_ts", 0)
        if pos != 0 and entry_ts == 0:
            td["entry_ts"] = ts
            entry_ts = ts
        if pos == 0:
            td["entry_ts"] = 0

        orders: List[Order] = []

        # Mean reversion entries only on volatility spikes, but bias toward long in uptrend.
        if pos == 0 and vol > vol_thr:
            if deviation < -2.2:
                qty = min(-od.sell_orders[best_ask], 28)
                if qty > 0:
                    orders.append(Order(PEPPER, best_ask, qty))
                    pos += qty
                    td["entry_ts"] = ts
            elif deviation > 2.8 and not trend_up:
                qty = min(od.buy_orders[best_bid], 20)
                if qty > 0:
                    orders.append(Order(PEPPER, best_bid, -qty))
                    pos -= qty
                    td["entry_ts"] = ts

        # Time-based exit discipline inspired by timed position management.
        if pos != 0 and td.get("entry_ts", 0) > 0:
            time_in_pos = ts - td["entry_ts"]
            if time_in_pos >= 2200:
                if pos > 0:
                    qty = min(pos, od.buy_orders[best_bid])
                    if qty > 0:
                        orders.append(Order(PEPPER, best_bid, -qty))
                        pos -= qty
                elif pos < 0:
                    qty = min(-pos, -od.sell_orders[best_ask])
                    if qty > 0:
                        orders.append(Order(PEPPER, best_ask, qty))
                        pos += qty
                if pos == 0:
                    td["entry_ts"] = 0

        # Supplemental carry layer to not miss the known PEPPER drift.
        progress = min(max(ts / 99900.0, 0.0), 1.0)
        target = 34.0 + (12.0 - 34.0) * progress
        if trend_up:
            target += 6.0
        target = max(0.0, min(46.0, target))

        inv_ratio = (pos - target) / LIMIT
        bid_px = math.floor(fair - 2 - 2.0 * inv_ratio)
        ask_px = math.ceil(fair + 2 - 2.0 * inv_ratio)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)
        buy_qty = min(buy_cap, max(1, int(20 * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(14 * (1 + inv_ratio))))

        if trend_up and pos < target - 2:
            sell_qty = max(0, sell_qty - 8)

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
            return 0.0
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
