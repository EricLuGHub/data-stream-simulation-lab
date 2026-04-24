from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
	"""R2 ASH high-risk variant tuned on round2 days -1 and 0."""

	def run(self, state: TradingState):
		td = self._load_td(state.traderData)
		result: Dict[str, List[Order]] = {}

		if ASH not in state.order_depths:
			return result, 0, json.dumps(td)

		od = state.order_depths[ASH]
		pos = state.position.get(ASH, 0)
		orders: List[Order] = []

		best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
		best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
		if best_bid is None or best_ask is None:
			result[ASH] = []
			return result, 0, json.dumps(td)

		mid = 0.5 * (best_bid + best_ask)
		spread = best_ask - best_bid

		ema = 0.34 * mid + 0.66 * td.get("ema", mid)
		td["ema"] = ema
		mids = td.get("mid_hist", [])
		mids.append(mid)
		mids = mids[-50:]
		td["mid_hist"] = mids

		short = mids[-10:] if len(mids) >= 10 else mids
		long = mids[-24:] if len(mids) >= 24 else mids
		short_mean = sum(short) / len(short)
		long_mean = sum(long) / len(long)
		z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

		wall_bid, wall_ask = self._get_walls(od, 12)
		wall_mid = 0.5 * (wall_bid + wall_ask)
		imb = self._imbalance(od)

		fair = 0.56 * wall_mid + 0.26 * ema + 0.18 * (0.6 * short_mean + 0.4 * long_mean) + 0.42 * imb

		take_width = 0
		if abs(z) >= 1.4:
			take_width = 0
		elif abs(z) <= 0.7:
			take_width = 1

		pos, take_orders = self._take(od, fair, pos, take_width, take_cap=7)
		orders.extend(take_orders)

		progress = min(max(state.timestamp / 99900.0, 0.0), 1.0)
		bucket = min(9, int(progress * 10))

		target_by_bucket = [35.0, 35.0, 34.0, 33.0, 31.0, 29.0, 30.0, 36.0, 39.0, 40.0]
		target = target_by_bucket[bucket]
		if short_mean > long_mean + 0.7:
			target += 4.0
		elif short_mean < long_mean - 0.7:
			target -= 2.0
		if z <= -1.5:
			target += 3.0
		if z >= 1.5:
			target -= 3.0
		target = max(-46, min(46, target))

		carry_floor = 0
		if progress >= 0.4 and short_mean > long_mean + 0.4:
			carry_floor = 31
		if progress >= 0.68 and short_mean > long_mean + 0.65:
			carry_floor = max(carry_floor, 40)

		if (z >= 2.4 and pos > target + 6 and pos > carry_floor) or (short_mean < long_mean - 0.5 and pos > target + 10 and pos > carry_floor):
			for bid_px2, bid_vol in sorted(od.buy_orders.items(), reverse=True):
				if bid_px2 >= fair + 1:
					qty = min(bid_vol, LIMIT + pos, 7)
					qty = min(qty, max(0, pos - carry_floor))
					if qty > 0:
						orders.append(Order(ASH, bid_px2, -qty))
						pos -= qty

		inv_ratio = (pos - target) / LIMIT
		half_spread = 2 if spread <= 12 else 3
		spread_px = max(1, half_spread - (1 if spread <= 3 else 0))
		bid_px = math.floor(fair - spread_px - 5.0 * inv_ratio + 0.24 * (short_mean - long_mean))
		ask_px = math.ceil(fair + spread_px - 5.0 * inv_ratio + 0.24 * (short_mean - long_mean))

		if best_bid + 1 < fair:
			bid_px = max(bid_px, best_bid + 1)
		if best_ask - 1 > fair:
			ask_px = min(ask_px, best_ask - 1)
		if bid_px >= ask_px:
			bid_px = ask_px - 1

		buy_cap = max(0, LIMIT - pos)
		sell_cap = max(0, LIMIT + pos)
		buy_base = 26
		sell_base = 21
		buy_qty = min(buy_cap, max(1, int(buy_base * (1 - 1.0 * inv_ratio))))
		sell_qty = min(sell_cap, max(1, int(sell_base * (1 + 0.8 * inv_ratio))))

		suppress_sell = (short_mean > long_mean + 0.65) and pos < target + 2
		suppress_sell = suppress_sell or (z <= -0.6) or (pos <= carry_floor)
		suppress_buy = (short_mean < long_mean - 0.95) and pos > target + 8 and z > 0.2

		if buy_qty > 0 and not suppress_buy:
			orders.append(Order(ASH, bid_px, buy_qty))
		if sell_qty > 0 and not suppress_sell:
			orders.append(Order(ASH, ask_px, -sell_qty))

		result[ASH] = self._clamp(orders, state.position.get(ASH, 0), LIMIT)
		return result, 0, json.dumps(td)

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

	def _take(self, od: OrderDepth, fair: float, pos: int, width: int, take_cap: int):
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

	def _std(self, xs: List[float]):
		if not xs:
			return 0.0
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
