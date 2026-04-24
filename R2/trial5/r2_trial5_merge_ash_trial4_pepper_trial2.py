from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
    """Merged R2 trial: ASH from trial4 + PEPPER from trial2."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        ash_td = td.get("ash", {})
        pepper_td = td.get("pepper", {})

        result: Dict[str, List[Order]] = {}

        if ASH in state.order_depths:
            result[ASH] = self._trade_ash(state, ash_td)
        if PEPPER in state.order_depths:
            result[PEPPER] = self._trade_pepper(state, pepper_td)

        td["ash"] = ash_td
        td["pepper"] = pepper_td
        return result, 0, json.dumps(td)

    def _trade_ash(self, state: TradingState, td: dict) -> List[Order]:
        od: OrderDepth = state.order_depths[ASH]
        if not od.buy_orders or not od.sell_orders:
            return []

        pos = state.position.get(ASH, 0)
        orders: List[Order] = []

        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid

        ema = 0.26 * mid + 0.74 * td.get("ema", mid)
        td["ema"] = ema
        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-40:]
        td["mid_hist"] = mids

        short = mids[-9:] if len(mids) >= 9 else mids
        long = mids[-22:] if len(mids) >= 22 else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

        wall_bid, wall_ask = self._get_walls(od, 11)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        fair = 0.53 * wall_mid + 0.27 * ema + 0.2 * (0.6 * short_mean + 0.4 * long_mean) + 0.5 * imb

        take_width = 1 if abs(z) < 1.1 else 0
        pos, take_orders = self._take_ash(od, fair, pos, take_width, take_cap=5)
        orders.extend(take_orders)

        inv = pos / LIMIT
        half_spread = 3 if spread <= 11 else 4
        bid_px = math.floor(fair - half_spread - 3.6 * inv)
        ask_px = math.ceil(fair + half_spread - 3.6 * inv)

        if best_bid + 2 < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - 2 > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        base = 15
        buy_qty = min(buy_cap, max(0, int(base * (1 - 0.75 * inv))))
        sell_qty = min(sell_cap, max(0, int(base * (1 + 0.72 * inv))))

        if pos > 34 or z > 1.7:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + 7)
        elif pos < -34 or z < -1.7:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + 7)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
            orders.append(Order(ASH, ask_px, -sell_qty))

        return self._clamp(orders, state.position.get(ASH, 0), LIMIT)

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
            no_fill = min(80, no_fill + 1)
        else:
            no_fill = 0
        td["prev_pos"] = pos
        td["no_fill"] = no_fill
        participation = min(1.0, no_fill / 22.0)

        heavy_bids = [p for p, v in od.buy_orders.items() if v >= 12]
        heavy_asks = [p for p, v in od.sell_orders.items() if -v >= 12]
        mm_bid = max(heavy_bids) if heavy_bids else best_bid
        mm_ask = min(heavy_asks) if heavy_asks else best_ask
        wall_mid = 0.5 * (mm_bid + mm_ask)

        ema = 0.32 * mid + 0.68 * td.get("ema", mid)
        td["ema"] = ema

        if "anchor_px" not in td:
            td["anchor_px"] = mid
            td["anchor_ts"] = ts
        drift = td["anchor_px"] + 0.001 * (ts - td["anchor_ts"])

        hist = td.get("mid_hist", [])
        hist.append(mid)
        hist = hist[-100:]
        td["mid_hist"] = hist

        short = hist[-8:] if len(hist) >= 8 else hist
        long = hist[-28:] if len(hist) >= 28 else hist
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        slope = short_mean - long_mean

        fair = 0.46 * wall_mid + 0.30 * drift + 0.24 * ema

        resid = mid - fair
        r_hist = td.get("r_hist", [])
        r_hist.append(resid)
        r_hist = r_hist[-140:]
        td["r_hist"] = r_hist
        z = resid / max(0.8, self._std(r_hist))

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        bucket = min(9, int(progress * 10))

        base_targets = [46.0, 46.0, 45.0, 44.0, 42.0, 40.0, 39.0, 45.0, 47.0, 48.0]
        target = base_targets[bucket]
        if slope > 1.0:
            target += 3.0
        elif slope < -0.8:
            target -= 3.0
        if z <= -1.0:
            target += 4.0
        if z >= 2.8:
            target -= 3.0
        target = max(4.0, min(50.0, target))

        confidence = self._confidence(slope, z, participation, progress)
        maf_bonus = 1.25 if confidence >= 0.62 else 1.0
        bonus_active = maf_bonus > 1.0

        orders: List[Order] = []

        take_edge = 1 + (1 if participation > 0.32 else 0)
        if bonus_active and abs(z) >= 1.6:
            take_edge += 1

        take_cap = 8 + int(5 * participation)
        if bonus_active:
            take_cap = int(math.ceil(take_cap * maf_bonus))

        if slope >= -0.35 or z <= -0.7:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= fair + take_edge:
                    qty = min(-ask_vol, LIMIT - pos, take_cap)
                    if qty > 0:
                        orders.append(Order(PEPPER, ask_px, qty))
                        pos += qty

        carry_floor = 0
        if progress >= 0.45 and slope > 0.6:
            carry_floor = 34
        if progress >= 0.70 and slope > 0.9:
            carry_floor = max(carry_floor, 42)

        if (z >= 3.0 and pos > target + 6 and pos > carry_floor) or (slope < -0.6 and pos > target + 10 and pos > carry_floor):
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= fair + 1:
                    qty = min(bid_vol, LIMIT + pos, 6)
                    qty = min(qty, max(0, pos - carry_floor))
                    if qty > 0:
                        orders.append(Order(PEPPER, bid_px, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT
        spread = 2 if slope >= 0 else 3
        spread = max(1, spread - (1 if participation > 0.55 else 0))
        if bonus_active and confidence >= 0.8:
            spread = max(1, spread - 1)

        bid_px = math.floor(fair - spread - 1.9 * inv_ratio + 0.17 * slope)
        ask_px = math.ceil(fair + spread - 1.9 * inv_ratio + 0.17 * slope)

        if participation > 0.62 and best_ask - best_bid <= 3:
            bid_px = max(bid_px, best_bid)
            ask_px = min(ask_px, best_ask)

        if bonus_active and confidence >= 0.72 and best_ask - best_bid <= 4:
            bid_px = max(bid_px, best_bid)
            ask_px = min(ask_px, best_ask)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_base = 26 + int(10 * participation)
        sell_base = 11 + int(3 * participation)
        if bonus_active:
            buy_base = int(math.ceil(buy_base * maf_bonus))
            sell_base = int(math.ceil(sell_base * maf_bonus))

        buy_qty = min(buy_cap, max(1, int(buy_base * (1 - inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(sell_base * (1 + inv_ratio))))

        suppress_sell = (slope > 0.5 and pos < target + 2) or (z <= -0.6) or (pos <= carry_floor)
        suppress_buy = (slope < -1.2 and pos > target + 9 and z > 0.3)

        if bonus_active and confidence < 0.7:
            suppress_buy = True

        if buy_qty > 0 and not suppress_buy:
            orders.append(Order(PEPPER, bid_px, buy_qty))
        if sell_qty > 0 and not suppress_sell:
            orders.append(Order(PEPPER, ask_px, -sell_qty))

        td["last_confidence"] = confidence
        td["bonus_active"] = bonus_active
        td["maf_bonus"] = maf_bonus

        return self._clamp(orders, state.position.get(PEPPER, 0), LIMIT)

    def _confidence(self, slope: float, z: float, participation: float, progress: float) -> float:
        score = 0.0
        score += min(0.35, max(0.0, slope) / 4.0)
        score += min(0.35, max(0.0, -z) / 5.0)
        score += min(0.20, participation * 0.20)
        if progress > 0.55:
            score += 0.08
        if progress > 0.78 and slope > 0:
            score += 0.07
        return min(1.0, score)

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

    def _imbalance(self, od: OrderDepth):
        b = sum(od.buy_orders.values())
        a = sum(-v for v in od.sell_orders.values())
        d = b + a
        return 0.0 if d == 0 else (b - a) / d

    def _take_ash(self, od: OrderDepth, fair: float, pos: int, width: int, take_cap: int):
        orders: List[Order] = []
        for ask, vol in sorted(od.sell_orders.items()):
            if ask <= fair - width:
                qty = min(-vol, LIMIT - pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, ask, qty))
                    pos += qty
        for bid, vol in sorted(od.buy_orders.items(), reverse=True):
            if bid >= fair + width:
                qty = min(vol, LIMIT + pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, bid, -qty))
                    pos -= qty
        return pos, orders

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
