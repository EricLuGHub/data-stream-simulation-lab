from pathlib import Path
import re
import subprocess


ROOT = Path("/Users/ericlu/Works/imcp4/imcprosp4")
TRIAL_DIR = ROOT / "R2" / "trial3"
TRIAL_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE = '''from datamodel import OrderDepth, TradingState, Order
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

		ema = __EMA_ALPHA__ * mid + __EMA_DECAY__ * td.get("ema", mid)
		td["ema"] = ema
		mids = td.get("mid_hist", [])
		mids.append(mid)
		mids = mids[-__HIST_LEN__:]
		td["mid_hist"] = mids

		short = mids[-__SHORT_LEN__:] if len(mids) >= __SHORT_LEN__ else mids
		long = mids[-__LONG_LEN__:] if len(mids) >= __LONG_LEN__ else mids
		short_mean = sum(short) / len(short)
		long_mean = sum(long) / len(long)
		z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

		wall_bid, wall_ask = self._get_walls(od, __WALL_MIN__)
		wall_mid = 0.5 * (wall_bid + wall_ask)
		imb = self._imbalance(od)

		fair = __WALL_WEIGHT__ * wall_mid + __EMA_WEIGHT__ * ema + __TREND_WEIGHT__ * (0.6 * short_mean + 0.4 * long_mean) + __IMB_WEIGHT__ * imb

		take_width = __TAKE_WIDTH__
		if abs(z) >= __WIDE_Z__:
			take_width = 0
		elif abs(z) <= __NARROW_Z__:
			take_width = 1

		pos, take_orders = self._take(od, fair, pos, take_width, take_cap=__TAKE_CAP__)
		orders.extend(take_orders)

		progress = min(max(state.timestamp / 99900.0, 0.0), 1.0)
		bucket = min(9, int(progress * 10))

		target_by_bucket = [__TARGETS__]
		target = target_by_bucket[bucket]
		if short_mean > long_mean + __TREND_BIAS_HI__:
			target += __TREND_UP__
		elif short_mean < long_mean - __TREND_BIAS_LO__:
			target -= __TREND_DN__
		if z <= -__BUY_Z__:
			target += __Z_BUY_TARGET__
		if z >= __SELL_Z__:
			target -= __Z_SELL_TARGET__
		target = max(-__TARGET_CLIP__, min(__TARGET_CLIP__, target))

		carry_floor = 0
		if progress >= __CARRY_PROGRESS_1__ and short_mean > long_mean + __CARRY_TREND_1__:
			carry_floor = __CARRY_FLOOR_1__
		if progress >= __CARRY_PROGRESS_2__ and short_mean > long_mean + __CARRY_TREND_2__:
			carry_floor = max(carry_floor, __CARRY_FLOOR_2__)

		if (z >= __UNWIND_Z__ and pos > target + __UNWIND_GAP__ and pos > carry_floor) or (short_mean < long_mean - __UNWIND_SLOPE__ and pos > target + __UNWIND_GAP2__ and pos > carry_floor):
			for bid_px2, bid_vol in sorted(od.buy_orders.items(), reverse=True):
				if bid_px2 >= fair + 1:
					qty = min(bid_vol, LIMIT + pos, __UNWIND_CAP__)
					qty = min(qty, max(0, pos - carry_floor))
					if qty > 0:
						orders.append(Order(ASH, bid_px2, -qty))
						pos -= qty

		inv_ratio = (pos - target) / LIMIT
		half_spread = __HALF_SPREAD_LO__ if spread <= __SPREAD_CUTOFF__ else __HALF_SPREAD_HI__
		spread_px = max(1, half_spread - (1 if spread <= __TIGHT_SPREAD__ else 0))
		bid_px = math.floor(fair - spread_px - __INV_SKEW__ * inv_ratio + __SLOPE_SKEW__ * (short_mean - long_mean))
		ask_px = math.ceil(fair + spread_px - __INV_SKEW__ * inv_ratio + __SLOPE_SKEW__ * (short_mean - long_mean))

		if best_bid + __IMPROVE_GAP__ < fair:
			bid_px = max(bid_px, best_bid + 1)
		if best_ask - __IMPROVE_GAP__ > fair:
			ask_px = min(ask_px, best_ask - 1)
		if bid_px >= ask_px:
			bid_px = ask_px - 1

		buy_cap = max(0, LIMIT - pos)
		sell_cap = max(0, LIMIT + pos)
		buy_base = __QUOTE_BUY_BASE__
		sell_base = __QUOTE_SELL_BASE__
		buy_qty = min(buy_cap, max(1, int(buy_base * (1 - __BUY_BIAS__ * inv_ratio))))
		sell_qty = min(sell_cap, max(1, int(sell_base * (1 + __SELL_BIAS__ * inv_ratio))))

		suppress_sell = (short_mean > long_mean + __SUPPRESS_TREND__) and pos < target + __SUPPRESS_SELL_GAP__
		suppress_sell = suppress_sell or (z <= -__SUPPRESS_SELL_Z__) or (pos <= carry_floor)
		suppress_buy = (short_mean < long_mean - __SUPPRESS_BUY_TREND__) and pos > target + __SUPPRESS_BUY_GAP__ and z > __SUPPRESS_BUY_Z__

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
'''


def run_bt(algo_path: Path, days: list[str]) -> tuple[int | None, str]:
	cmd = [
		str(ROOT / ".venv" / "bin" / "prosperity4btest"),
		str(algo_path),
		*days,
		"--data",
		str(ROOT / "R2"),
		"--merge-pnl",
		"--no-progress",
		"--no-out",
	]
	proc = subprocess.run(cmd, capture_output=True, text=True)
	text = proc.stdout + "\n" + proc.stderr
	if proc.returncode != 0:
		return None, text
	m = re.findall(r"Total profit:\s*([\-\d,]+)", text)
	if not m:
		return None, text
	return int(m[-1].replace(",", "")), text


def fill_template(params: dict) -> str:
	code = TEMPLATE
	for key, value in params.items():
		code = code.replace(f"__{key}__", str(value))
	return code


def main() -> None:
	param_grid = [
		{
			"EMA_ALPHA": 0.30,
			"EMA_DECAY": 0.70,
			"HIST_LEN": 45,
			"SHORT_LEN": 12,
			"LONG_LEN": 26,
			"WALL_MIN": 10,
			"WALL_WEIGHT": 0.58,
			"EMA_WEIGHT": 0.24,
			"TREND_WEIGHT": 0.18,
			"IMB_WEIGHT": 0.40,
			"TAKE_WIDTH": 1,
			"WIDE_Z": 1.6,
			"NARROW_Z": 0.8,
			"TAKE_CAP": 6,
			"HALF_SPREAD_LO": 2,
			"HALF_SPREAD_HI": 3,
			"SPREAD_CUTOFF": 14,
			"INV_SKEW": 4.6,
			"SLOPE_SKEW": 0.22,
			"IMPROVE_GAP": 2,
			"QUOTE_BUY_BASE": 24,
			"QUOTE_SELL_BASE": 20,
			"BUY_BIAS": 0.9,
			"SELL_BIAS": 0.75,
			"FORCE_SELL_POS": 35,
			"SELL_Z": 1.6,
			"SELL_EXTRA": 6,
			"BUY_Z": 1.6,
			"BUY_EXTRA": 6,
			"TARGETS": "34.0, 34.0, 33.0, 32.0, 30.0, 28.0, 29.0, 35.0, 38.0, 39.0",
			"TREND_BIAS_HI": 0.8,
			"TREND_BIAS_LO": 0.8,
			"TREND_UP": 3.0,
			"TREND_DN": 2.0,
			"Z_BUY_TARGET": 3.0,
			"Z_SELL_TARGET": 3.0,
			"TARGET_CLIP": 45,
			"CARRY_PROGRESS_1": 0.42,
			"CARRY_PROGRESS_2": 0.70,
			"CARRY_TREND_1": 0.45,
			"CARRY_TREND_2": 0.70,
			"CARRY_FLOOR_1": 30,
			"CARRY_FLOOR_2": 39,
			"UNWIND_Z": 2.6,
			"UNWIND_GAP": 6,
			"UNWIND_SLOPE": 0.55,
			"UNWIND_GAP2": 10,
			"UNWIND_CAP": 6,
			"TIGHT_SPREAD": 3,
			"SPREAD_BIAS_HI": 4.1,
			"SPREAD_BIAS_LO": 3.6,
			"SLOPE_QUOTE": 0.18,
			"PASSIVE_SPREAD": 4,
			"PASSIVE_Z": 0.55,
			"SUPPRESS_TREND": 0.7,
			"SUPPRESS_SELL_GAP": 2,
			"SUPPRESS_SELL_Z": 0.65,
			"SUPPRESS_BUY_TREND": 1.0,
			"SUPPRESS_BUY_GAP": 8,
			"SUPPRESS_BUY_Z": 0.25,
		},
		{
			"EMA_ALPHA": 0.34,
			"EMA_DECAY": 0.66,
			"HIST_LEN": 50,
			"SHORT_LEN": 10,
			"LONG_LEN": 24,
			"WALL_MIN": 12,
			"WALL_WEIGHT": 0.56,
			"EMA_WEIGHT": 0.26,
			"TREND_WEIGHT": 0.18,
			"IMB_WEIGHT": 0.42,
			"TAKE_WIDTH": 0,
			"WIDE_Z": 1.4,
			"NARROW_Z": 0.7,
			"TAKE_CAP": 7,
			"HALF_SPREAD_LO": 2,
			"HALF_SPREAD_HI": 3,
			"SPREAD_CUTOFF": 12,
			"INV_SKEW": 5.0,
			"SLOPE_SKEW": 0.24,
			"IMPROVE_GAP": 1,
			"QUOTE_BUY_BASE": 26,
			"QUOTE_SELL_BASE": 21,
			"BUY_BIAS": 1.0,
			"SELL_BIAS": 0.8,
			"FORCE_SELL_POS": 34,
			"SELL_Z": 1.5,
			"SELL_EXTRA": 7,
			"BUY_Z": 1.5,
			"BUY_EXTRA": 7,
			"TARGETS": "35.0, 35.0, 34.0, 33.0, 31.0, 29.0, 30.0, 36.0, 39.0, 40.0",
			"TREND_BIAS_HI": 0.7,
			"TREND_BIAS_LO": 0.7,
			"TREND_UP": 4.0,
			"TREND_DN": 2.0,
			"Z_BUY_TARGET": 3.0,
			"Z_SELL_TARGET": 3.0,
			"TARGET_CLIP": 46,
			"CARRY_PROGRESS_1": 0.40,
			"CARRY_PROGRESS_2": 0.68,
			"CARRY_TREND_1": 0.40,
			"CARRY_TREND_2": 0.65,
			"CARRY_FLOOR_1": 31,
			"CARRY_FLOOR_2": 40,
			"UNWIND_Z": 2.4,
			"UNWIND_GAP": 6,
			"UNWIND_SLOPE": 0.50,
			"UNWIND_GAP2": 10,
			"UNWIND_CAP": 7,
			"TIGHT_SPREAD": 3,
			"SPREAD_BIAS_HI": 4.3,
			"SPREAD_BIAS_LO": 3.8,
			"SLOPE_QUOTE": 0.20,
			"PASSIVE_SPREAD": 4,
			"PASSIVE_Z": 0.50,
			"SUPPRESS_TREND": 0.65,
			"SUPPRESS_SELL_GAP": 2,
			"SUPPRESS_SELL_Z": 0.60,
			"SUPPRESS_BUY_TREND": 0.95,
			"SUPPRESS_BUY_GAP": 8,
			"SUPPRESS_BUY_Z": 0.20,
		},
		{
			"EMA_ALPHA": 0.38,
			"EMA_DECAY": 0.62,
			"HIST_LEN": 55,
			"SHORT_LEN": 10,
			"LONG_LEN": 28,
			"WALL_MIN": 12,
			"WALL_WEIGHT": 0.54,
			"EMA_WEIGHT": 0.28,
			"TREND_WEIGHT": 0.18,
			"IMB_WEIGHT": 0.44,
			"TAKE_WIDTH": 0,
			"WIDE_Z": 1.35,
			"NARROW_Z": 0.75,
			"TAKE_CAP": 8,
			"HALF_SPREAD_LO": 2,
			"HALF_SPREAD_HI": 3,
			"SPREAD_CUTOFF": 11,
			"INV_SKEW": 5.2,
			"SLOPE_SKEW": 0.25,
			"IMPROVE_GAP": 1,
			"QUOTE_BUY_BASE": 28,
			"QUOTE_SELL_BASE": 22,
			"BUY_BIAS": 1.0,
			"SELL_BIAS": 0.85,
			"FORCE_SELL_POS": 32,
			"SELL_Z": 1.4,
			"SELL_EXTRA": 7,
			"BUY_Z": 1.4,
			"BUY_EXTRA": 7,
			"TARGETS": "36.0, 36.0, 35.0, 34.0, 32.0, 30.0, 31.0, 37.0, 40.0, 41.0",
			"TREND_BIAS_HI": 0.7,
			"TREND_BIAS_LO": 0.7,
			"TREND_UP": 4.0,
			"TREND_DN": 2.0,
			"Z_BUY_TARGET": 4.0,
			"Z_SELL_TARGET": 3.0,
			"TARGET_CLIP": 47,
			"CARRY_PROGRESS_1": 0.40,
			"CARRY_PROGRESS_2": 0.66,
			"CARRY_TREND_1": 0.40,
			"CARRY_TREND_2": 0.60,
			"CARRY_FLOOR_1": 32,
			"CARRY_FLOOR_2": 41,
			"UNWIND_Z": 2.3,
			"UNWIND_GAP": 5,
			"UNWIND_SLOPE": 0.48,
			"UNWIND_GAP2": 9,
			"UNWIND_CAP": 8,
			"TIGHT_SPREAD": 3,
			"SPREAD_BIAS_HI": 4.4,
			"SPREAD_BIAS_LO": 3.9,
			"SLOPE_QUOTE": 0.20,
			"PASSIVE_SPREAD": 4,
			"PASSIVE_Z": 0.50,
			"SUPPRESS_TREND": 0.65,
			"SUPPRESS_SELL_GAP": 2,
			"SUPPRESS_SELL_Z": 0.60,
			"SUPPRESS_BUY_TREND": 0.95,
			"SUPPRESS_BUY_GAP": 8,
			"SUPPRESS_BUY_Z": 0.20,
		},
	]

	results: list[tuple[int, dict, Path]] = []
	for i, params in enumerate(param_grid):
		code = fill_template(params)
		candidate = TRIAL_DIR / f"_cand_{i:02d}.py"
		candidate.write_text(code)

		train_profit, _ = run_bt(candidate, ["2--1", "2-0"])
		print(f"candidate {i+1}/{len(param_grid)} train_profit={train_profit}")
		if train_profit is not None:
			results.append((train_profit, params, candidate))

	if not results:
		raise SystemExit("No successful candidate backtests in sweep")

	results.sort(key=lambda x: x[0], reverse=True)
	best_train, best_params, best_candidate = results[0]
	holdout_profit, _ = run_bt(best_candidate, ["2-1"])
	full_profit, full_out = run_bt(best_candidate, ["2--1", "2-0", "2-1"])

	final_path = TRIAL_DIR / "r2_ash_highrisk_tuned.py"
	final_path.write_text(best_candidate.read_text())

	(TRIAL_DIR / "summary.md").write_text(
		"# R2 Trial 3 - ASH High-Risk Tuned\n\n"
		"Tuned on round2 days -1 and 0, then validated on day 1.\n\n"
		f"- Best training total (2--1, 2-0): **{best_train:,}**\n"
		f"- Holdout test (2-1): **{holdout_profit if holdout_profit is not None else 'N/A'}**\n"
		f"- Full round 2 total: **{full_profit if full_profit is not None else 'N/A'}**\n"
		f"- Params: {best_params}\n"
		f"- Strategy file: {final_path.name}\n"
	)

	(TRIAL_DIR / "report.md").write_text(
		"# R2 Trial 3 ASH Report\n\n"
		"## Objective\n"
		"Tune a higher-risk ASH-only strategy on round 2 days -1 and 0, then report the full round 2 PnL across all days.\n\n"
		"## Setup\n"
		"- Training days: round 2 day -1 and day 0\n"
		"- Holdout day: round 2 day 1\n"
		"- Market scope: `ASH_COATED_OSMIUM` only\n"
		"- Style: higher-risk carry with faster inventory rotation than the passive round-1 baseline\n\n"
		f"The final tuned strategy was saved at [{final_path.name}]({final_path.name}).\n\n"
		"## Tuning outcome\n"
		f"Best training result on days -1 and 0: **{best_train:,}**\n\n"
		"## Holdout and full backtest\n"
		f"Holdout day 1 profit: **{holdout_profit if holdout_profit is not None else 'N/A'}**\n\n"
		f"Full round 2 profit: **{full_profit if full_profit is not None else 'N/A'}**\n\n"
		"## Daily PnL\n"
		"| Day | ASH PnL |\n"
		"|---:|---:|\n"
		"| -1 | pending |\n"
		"| 0 | pending |\n"
		"| 1 | pending |\n\n"
		"## Interpretation\n"
		"This report will be finalized after the full backtest output is parsed.\n"
	)

	(TRIAL_DIR / "full_round2_backtest.log").write_text(full_out)

	print("BEST_TRAIN", best_train)
	print("BEST_PARAMS", best_params)
	print("HOLDOUT_DAY1", holdout_profit)
	print("FULL_ROUND2", full_profit)
	print("FINAL_FILE", final_path)

	for _, _, candidate in results:
		if candidate != best_candidate and candidate.exists():
			candidate.unlink()
	if best_candidate.exists() and best_candidate.name.startswith("_cand_"):
		best_candidate.unlink()


if __name__ == "__main__":
	main()
