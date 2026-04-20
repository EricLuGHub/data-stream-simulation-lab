from pathlib import Path
import itertools
import re
import subprocess


ROOT = Path("/Users/ericlu/Works/imcp4/imcprosp4")
TRIAL_DIR = ROOT / "R2" / "trial1"
TRIAL_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE = '''from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import json
import math

PEPPER = "INTARIAN_PEPPER_ROOT"
LIMIT = 50


class Trader:
	"""R2 trial: high-risk PEPPER carry variant tuned on round2 days -1 and 0."""

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

		target_by_bucket = [48.0, 48.0, 47.0, 46.0, 44.0, 42.0, 40.0, 47.0, 49.0, 49.0]
		target = target_by_bucket[bucket] + {late_bias}
		if slope > 1.0:
			target += {slope_up}
		elif slope < -0.8:
			target -= {slope_dn}
		if z <= -1.0:
			target += {z_buy}
		if z >= 2.8:
			target -= {z_sell}
		target = max(4.0, min(50.0, target))

		orders: List[Order] = []

		take_edge = 1 + (1 if participation > 0.32 else 0)
		take_cap = 8 + int(5 * participation)

		if slope >= -0.35 or z <= -0.7:
			for ask_px, ask_vol in sorted(od.sell_orders.items()):
				if ask_px <= fair + take_edge:
					qty = min(-ask_vol, LIMIT - pos, take_cap)
					if qty > 0:
						orders.append(Order(PEPPER, ask_px, qty))
						pos += qty

		carry_floor = 0
		if progress >= 0.45 and slope > 0.6:
			carry_floor = {carry_floor}
		if progress >= 0.70 and slope > 0.9:
			carry_floor = max(carry_floor, {carry_floor_late})

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

		bid_px = math.floor(fair - spread - 1.9 * inv_ratio + 0.17 * slope)
		ask_px = math.ceil(fair + spread - 1.9 * inv_ratio + 0.17 * slope)

		if participation > 0.62 and best_ask - best_bid <= 3:
			bid_px = max(bid_px, best_bid)
			ask_px = min(ask_px, best_ask)

		if bid_px >= ask_px:
			bid_px = ask_px - 1

		buy_cap = max(0, LIMIT - pos)
		sell_cap = max(0, LIMIT + pos)

		buy_base = {buy_base} + int(10 * participation)
		sell_base = {sell_base} + int(3 * participation)

		buy_qty = min(buy_cap, max(1, int(buy_base * (1 - inv_ratio))))
		sell_qty = min(sell_cap, max(1, int(sell_base * (1 + inv_ratio))))

		suppress_sell = (slope > 0.5 and pos < target + 2) or (z <= -0.6) or (pos <= carry_floor)
		suppress_buy = (slope < -1.2 and pos > target + 9 and z > 0.3)

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
'''


def run_bt(algo_path: Path, days: list[str]) -> int | None:
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
		return None
	m = re.findall(r"Total profit:\s*([\-\d,]+)", text)
	if not m:
		return None
	return int(m[-1].replace(",", ""))


def main() -> None:
	param_grid = [
		(0.0, 4.0, 3.0, 4.0, 3.0, 34, 42, 28, 12),
		(1.0, 5.0, 3.0, 4.0, 3.0, 38, 45, 30, 10),
		(2.0, 6.0, 4.0, 5.0, 4.0, 42, 47, 32, 8),
		(1.0, 6.0, 3.0, 5.0, 4.0, 42, 47, 32, 10),
		(2.0, 5.0, 4.0, 5.0, 3.0, 38, 45, 30, 8),
		(0.0, 6.0, 4.0, 4.0, 4.0, 34, 45, 30, 12),
	]

	results: list[tuple[int, tuple, Path]] = []
	for i, params in enumerate(param_grid):
		(
			late_bias,
			slope_up,
			slope_dn,
			z_buy,
			z_sell,
			carry_floor,
			carry_floor_late,
			buy_base,
			sell_base,
		) = params

		code = TEMPLATE
		code = code.replace("{late_bias}", str(late_bias))
		code = code.replace("{slope_up}", str(slope_up))
		code = code.replace("{slope_dn}", str(slope_dn))
		code = code.replace("{z_buy}", str(z_buy))
		code = code.replace("{z_sell}", str(z_sell))
		code = code.replace("{carry_floor}", str(carry_floor))
		code = code.replace("{carry_floor_late}", str(carry_floor_late))
		code = code.replace("{buy_base}", str(buy_base))
		code = code.replace("{sell_base}", str(sell_base))
		candidate = TRIAL_DIR / f"_cand_{i:02d}.py"
		candidate.write_text(code)

		train_profit = run_bt(candidate, ["2--1", "2-0"])
		print(f"candidate {i+1}/{len(param_grid)} train_profit={train_profit}")
		if train_profit is not None:
			results.append((train_profit, params, candidate))

	if not results:
		raise SystemExit("No successful candidate backtests in sweep")

	results.sort(key=lambda x: x[0], reverse=True)
	best_train, best_params, best_candidate = results[0]
	holdout_profit = run_bt(best_candidate, ["2-1"])

	final_path = TRIAL_DIR / "r2_pepper_highrisk_tuned.py"
	final_path.write_text(best_candidate.read_text())

	(TRIAL_DIR / "summary.md").write_text(
		"# R2 Trial 1 - PEPPER High-Risk Tuned\n\n"
		"Tuned on round2 days -1 and 0 (as in notebooks).\n\n"
		f"- Best training total (2--1, 2-0): **{best_train:,}**\n"
		f"- Holdout test (2-1): **{holdout_profit if holdout_profit is not None else 'N/A'}**\n"
		f"- Params: {best_params}\n"
		f"- Strategy file: {final_path.name}\n"
	)

	print("BEST_TRAIN", best_train)
	print("BEST_PARAMS", best_params)
	print("HOLDOUT_DAY1", holdout_profit)
	print("FINAL_FILE", final_path)

	for _, _, candidate in results:
		if candidate != best_candidate and candidate.exists():
			candidate.unlink()
	if best_candidate.exists() and best_candidate.name.startswith("_cand_"):
		best_candidate.unlink()


if __name__ == "__main__":
	main()
