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
    """Trial 26: merged trial14 ASH + trial23 PEPPER."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if ASH in state.order_depths:
            result[ASH] = self._trade_ash(state, td)

        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, td)

        return result, 0, json.dumps(td)

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

    def _trade_pepper(self, state: TradingState, td: dict) -> List[Order]:
        od = state.order_depths[PEPPER]
        pos = state.position.get(PEPPER, 0)
        if not od.buy_orders or not od.sell_orders:
            return []

        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        ts = state.timestamp

        prev_pos = td.get("pepper_prev_pos", pos)
        no_fill_steps = td.get("pepper_no_fill_steps", 0)
        if pos == prev_pos:
            no_fill_steps = min(24, no_fill_steps + 1)
        else:
            no_fill_steps = 0
        td["pepper_prev_pos"] = pos
        td["pepper_no_fill_steps"] = no_fill_steps
        participation = min(1.0, no_fill_steps / 18.0)

        filt_bids = [p for p, v in od.buy_orders.items() if abs(v) >= 10]
        filt_asks = [p for p, v in od.sell_orders.items() if abs(v) >= 10]
        mm_bid = max(filt_bids) if filt_bids else best_bid
        mm_ask = min(filt_asks) if filt_asks else best_ask
        wall_mid = 0.5 * (mm_bid + mm_ask)

        hist = td.get("pepper_mid_hist", [])
        hist.append(mid)
        hist = hist[-80:]
        td["pepper_mid_hist"] = hist

        short = hist[-8:] if len(hist) >= 8 else hist
        long = hist[-28:] if len(hist) >= 28 else hist
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)

        trend = 0
        if short_mean > long_mean + 0.6:
            trend = 1
        elif short_mean < long_mean - 0.6:
            trend = -1

        if "pepper_anchor_px" not in td:
            td["pepper_anchor_px"] = mid
            td["pepper_anchor_ts"] = ts
        drift = td["pepper_anchor_px"] + 0.001 * (ts - td["pepper_anchor_ts"])

        fair = 0.55 * wall_mid + 0.25 * short_mean + 0.20 * drift

        resid = mid - fair
        r_hist = td.get("pepper_resid_hist", [])
        r_hist.append(resid)
        r_hist = r_hist[-100:]
        td["pepper_resid_hist"] = r_hist
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
                qty = min(-ask_vol, LIMITS[PEPPER] - pos, buy_take_cap)
                if qty > 0:
                    orders.append(Order(PEPPER, ask_px, qty))
                    pos += qty

        if z >= 2.8 and pos > target + 3:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 1:
                    qty = min(bid_vol, LIMITS[PEPPER] + pos, 7)
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMITS[PEPPER]
        base_spread = 2 if trend >= 0 else 3
        spread = base_spread - 1 if (participation > 0.75 and trend >= 0 and (best_ask - best_bid) <= 3) else base_spread
        bid_px = math.floor(fair - spread - 2.0 * inv_ratio)
        ask_px = math.ceil(fair + spread - 2.0 * inv_ratio)

        # If the strategy has not been filling, lean quotes one tick toward touch.
        if participation > 0.60:
            bid_px = max(bid_px, best_bid)
            ask_px = min(ask_px, best_ask)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMITS[PEPPER] - pos)
        sell_cap = max(0, LIMITS[PEPPER] + pos)

        buy_qty = min(buy_cap, max(1, int((30 + 3 * participation) * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int((18 + 2 * participation) * (1 + inv_ratio))))

        suppress_sell = (trend > 0 and pos < target - 2) or (z <= -1.4)
        suppress_buy = (trend < 0 and pos > target + 8)

        if buy_qty > 0 and not suppress_buy:
            orders.append(Order(PEPPER, bid_px, buy_qty))
        if sell_qty > 0 and not suppress_sell:
            orders.append(Order(PEPPER, ask_px, -sell_qty))

        return self._clamp(orders, state.position.get(PEPPER, 0), LIMITS[PEPPER])

    def _load_td(self, raw: str):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

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

    def _imbalance(self, od: OrderDepth) -> float:
        b = sum(od.buy_orders.values())
        a = sum(-v for v in od.sell_orders.values())
        d = b + a
        return 0.0 if d == 0 else (b - a) / d

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

    def _std(self, xs: List[float]) -> float:
        if len(xs) < 2:
            return 1.0
        m = sum(xs) / len(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

    def _clamp(self, orders: List[Order], cur: int, limit: int):
        buy = sum(o.quantity for o in orders if o.quantity > 0)
        sell = sum(-o.quantity for o in orders if o.quantity < 0)
        if cur + buy > limit and buy > 0:
            s = max(0.0, (limit - cur) / buy)
            for o in orders:
                if o.quantity > 0:
                    o.quantity = int(o.quantity * s)
        if cur - sell < -limit and sell > 0:
            s = max(0.0, (limit + cur) / sell)
            for o in orders:
                if o.quantity < 0:
                    o.quantity = -int((-o.quantity) * s)
        return [o for o in orders if o.quantity != 0]
