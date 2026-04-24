from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
	"""R2 PEPPER variant that reserves a bonus quote layer for strong signals.

	The simulator does not expose an explicit MAF hook, so this strategy treats the
	contest rule as a conditional aggressiveness layer: the core quote logic stays
	conservative, while the additional 25% of notional is only used when the signal
	quality is high enough to justify paying for extra access in a real submission.
	"""

	def run(self, state: TradingState):
		dt = self._load_td(state.traderData)
		result: Dict[str, List[Order]] = {}

		if PEPPER in state.order_depths:
			result[PEPPER] = self._trade_pepper(state, dt)

		return result, 0, json.dumps(dt)

	def _trade_pepper(self, state: TradingState, dt: dict) -> List[Order]:
		od: OrderDepth = state.order_depths[PEPPER]
		if not od.buy_orders or not od.sell_orders:
			return []

		pos = state.position.get(PEPPER, 0)
		best_bid = max(od.buy_orders)
		best_ask = min(od.sell_orders)
		mid = 0.5 * (best_bid + best_ask)
		ts = state.timestamp

		prev_pos = dt.get("prev_pos", pos)
		no_fill = dt.get("no_fill", 0)
		if pos == prev_pos:
			no_fill = min(80, no_fill + 1)
		else:
			no_fill = 0
		dt["prev_pos"] = pos
		dt["no_fill"] = no_fill
		participation = min(1.0, no_fill / 22.0)

		heavy_bids = [p for p, v in od.buy_orders.items() if v >= 12]
		heavy_asks = [p for p, v in od.sell_orders.items() if -v >= 12]
		mm_bid = max(heavy_bids) if heavy_bids else best_bid
		mm_ask = min(heavy_asks) if heavy_asks else best_ask
		wall_mid = 0.5 * (mm_bid + mm_ask)

		ema = 0.32 * mid + 0.68 * dt.get("ema", mid)
		dt["ema"] = ema

		if "anchor_px" not in dt:
			dt["anchor_px"] = mid
			dt["anchor_ts"] = ts
		drift = dt["anchor_px"] + 0.001 * (ts - dt["anchor_ts"])

		hist = dt.get("mid_hist", [])
		hist.append(mid)
		hist = hist[-100:]
		dt["mid_hist"] = hist

		short = hist[-8:] if len(hist) >= 8 else hist
		long = hist[-28:] if len(hist) >= 28 else hist
		short_mean = sum(short) / len(short)
		long_mean = sum(long) / len(long)
		slope = short_mean - long_mean

		fair = 0.46 * wall_mid + 0.30 * drift + 0.24 * ema

		resid = mid - fair
		r_hist = dt.get("r_hist", [])
		r_hist.append(resid)
		r_hist = r_hist[-140:]
		dt["r_hist"] = r_hist
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

		dt["last_confidence"] = confidence
		dt["bonus_active"] = bonus_active
		dt["maf_bonus"] = maf_bonus

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