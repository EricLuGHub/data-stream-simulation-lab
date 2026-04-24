from pathlib import Path
import re
import subprocess


ROOT = Path("/Users/ericlu/Works/imcp4/imcprosp4")
TRIAL_DIR = ROOT / "R2" / "trial4"
TRIAL_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE = '''from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
    """R2 Trial 4: trial14-style ASH with mild parameter tuning."""

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

        take_width = __TAKE_WIDTH__ if abs(z) < __TAKE_Z_RELAX__ else 0
        pos, take_orders = self._take(od, fair, pos, take_width, take_cap=__TAKE_CAP__)
        orders.extend(take_orders)

        inv = pos / LIMIT
        half_spread = __HALF_SPREAD_LO__ if spread <= __SPREAD_CUTOFF__ else __HALF_SPREAD_HI__
        bid_px = math.floor(fair - half_spread - __INV_SKEW__ * inv)
        ask_px = math.ceil(fair + half_spread - __INV_SKEW__ * inv)

        if best_bid + __IMPROVE_GAP__ < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - __IMPROVE_GAP__ > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        base = __BASE_SIZE__
        buy_qty = min(buy_cap, max(0, int(base * (1 - __BUY_BIAS__ * inv))))
        sell_qty = min(sell_cap, max(0, int(base * (1 + __SELL_BIAS__ * inv))))

        if pos > __FORCE_POS__ or z > __FORCE_Z__:
            buy_qty = 0
            sell_qty = min(sell_cap, sell_qty + __FORCE_EXTRA__)
        elif pos < -__FORCE_POS__ or z < -__FORCE_Z__:
            sell_qty = 0
            buy_qty = min(buy_cap, buy_qty + __FORCE_EXTRA__)

        if buy_qty > 0:
            orders.append(Order(ASH, bid_px, buy_qty))
        if sell_qty > 0:
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


def day_profit(text: str, day: int) -> int | None:
    m = re.search(rf"Round 2 day {day}:\s*([\-\d,]+)", text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def main() -> None:
    param_grid = [
        {
            "EMA_ALPHA": 0.22,
            "EMA_DECAY": 0.78,
            "HIST_LEN": 35,
            "SHORT_LEN": 10,
            "LONG_LEN": 24,
            "WALL_MIN": 12,
            "WALL_WEIGHT": 0.55,
            "EMA_WEIGHT": 0.25,
            "TREND_WEIGHT": 0.20,
            "IMB_WEIGHT": 0.45,
            "TAKE_WIDTH": 1,
            "TAKE_Z_RELAX": 1.0,
            "TAKE_CAP": 4,
            "HALF_SPREAD_LO": 3,
            "HALF_SPREAD_HI": 4,
            "SPREAD_CUTOFF": 12,
            "INV_SKEW": 3.8,
            "IMPROVE_GAP": 2,
            "BASE_SIZE": 14,
            "BUY_BIAS": 0.70,
            "SELL_BIAS": 0.70,
            "FORCE_POS": 35,
            "FORCE_Z": 1.8,
            "FORCE_EXTRA": 6,
        },
        {
            "EMA_ALPHA": 0.24,
            "EMA_DECAY": 0.76,
            "HIST_LEN": 38,
            "SHORT_LEN": 10,
            "LONG_LEN": 24,
            "WALL_MIN": 11,
            "WALL_WEIGHT": 0.54,
            "EMA_WEIGHT": 0.26,
            "TREND_WEIGHT": 0.20,
            "IMB_WEIGHT": 0.48,
            "TAKE_WIDTH": 1,
            "TAKE_Z_RELAX": 1.1,
            "TAKE_CAP": 5,
            "HALF_SPREAD_LO": 3,
            "HALF_SPREAD_HI": 4,
            "SPREAD_CUTOFF": 12,
            "INV_SKEW": 3.7,
            "IMPROVE_GAP": 2,
            "BASE_SIZE": 15,
            "BUY_BIAS": 0.72,
            "SELL_BIAS": 0.70,
            "FORCE_POS": 34,
            "FORCE_Z": 1.7,
            "FORCE_EXTRA": 6,
        },
        {
            "EMA_ALPHA": 0.26,
            "EMA_DECAY": 0.74,
            "HIST_LEN": 40,
            "SHORT_LEN": 9,
            "LONG_LEN": 22,
            "WALL_MIN": 11,
            "WALL_WEIGHT": 0.53,
            "EMA_WEIGHT": 0.27,
            "TREND_WEIGHT": 0.20,
            "IMB_WEIGHT": 0.50,
            "TAKE_WIDTH": 1,
            "TAKE_Z_RELAX": 1.1,
            "TAKE_CAP": 5,
            "HALF_SPREAD_LO": 3,
            "HALF_SPREAD_HI": 4,
            "SPREAD_CUTOFF": 11,
            "INV_SKEW": 3.6,
            "IMPROVE_GAP": 2,
            "BASE_SIZE": 15,
            "BUY_BIAS": 0.75,
            "SELL_BIAS": 0.72,
            "FORCE_POS": 34,
            "FORCE_Z": 1.7,
            "FORCE_EXTRA": 7,
        },
        {
            "EMA_ALPHA": 0.24,
            "EMA_DECAY": 0.76,
            "HIST_LEN": 36,
            "SHORT_LEN": 10,
            "LONG_LEN": 24,
            "WALL_MIN": 12,
            "WALL_WEIGHT": 0.56,
            "EMA_WEIGHT": 0.24,
            "TREND_WEIGHT": 0.20,
            "IMB_WEIGHT": 0.43,
            "TAKE_WIDTH": 2,
            "TAKE_Z_RELAX": 1.0,
            "TAKE_CAP": 4,
            "HALF_SPREAD_LO": 3,
            "HALF_SPREAD_HI": 4,
            "SPREAD_CUTOFF": 12,
            "INV_SKEW": 3.9,
            "IMPROVE_GAP": 2,
            "BASE_SIZE": 14,
            "BUY_BIAS": 0.70,
            "SELL_BIAS": 0.70,
            "FORCE_POS": 35,
            "FORCE_Z": 1.8,
            "FORCE_EXTRA": 6,
        },
        {
            "EMA_ALPHA": 0.28,
            "EMA_DECAY": 0.72,
            "HIST_LEN": 42,
            "SHORT_LEN": 9,
            "LONG_LEN": 22,
            "WALL_MIN": 10,
            "WALL_WEIGHT": 0.52,
            "EMA_WEIGHT": 0.28,
            "TREND_WEIGHT": 0.20,
            "IMB_WEIGHT": 0.50,
            "TAKE_WIDTH": 1,
            "TAKE_Z_RELAX": 1.2,
            "TAKE_CAP": 5,
            "HALF_SPREAD_LO": 3,
            "HALF_SPREAD_HI": 4,
            "SPREAD_CUTOFF": 11,
            "INV_SKEW": 3.5,
            "IMPROVE_GAP": 2,
            "BASE_SIZE": 16,
            "BUY_BIAS": 0.78,
            "SELL_BIAS": 0.74,
            "FORCE_POS": 33,
            "FORCE_Z": 1.6,
            "FORCE_EXTRA": 7,
        },
    ]

    results: list[tuple[int, dict, Path]] = []
    for i, params in enumerate(param_grid):
        candidate = TRIAL_DIR / f"_cand_{i:02d}.py"
        candidate.write_text(fill_template(params))
        train_profit, _ = run_bt(candidate, ["2--1", "2-0"])
        print(f"candidate {i + 1}/{len(param_grid)} train_profit={train_profit}")
        if train_profit is not None:
            results.append((train_profit, params, candidate))

    if not results:
        raise SystemExit("No successful candidate backtests in sweep")

    results.sort(key=lambda x: x[0], reverse=True)
    best_train, best_params, best_candidate = results[0]

    holdout_profit, holdout_out = run_bt(best_candidate, ["2-1"])
    full_profit, full_out = run_bt(best_candidate, ["2--1", "2-0", "2-1"])

    day_m1 = day_profit(full_out, -1)
    day_0 = day_profit(full_out, 0)
    day_1 = day_profit(full_out, 1)

    final_path = TRIAL_DIR / "r2_ash_trial14_tuned.py"
    final_path.write_text(best_candidate.read_text())
    (TRIAL_DIR / "day1_backtest.log").write_text(holdout_out)
    (TRIAL_DIR / "full_round2_backtest.log").write_text(full_out)

    (TRIAL_DIR / "summary.md").write_text(
        "# R2 Trial 4 - Trial14 Tuned (Lower-Risk)\n\n"
        "Tuned on round2 days -1 and 0, then validated on day 1.\n\n"
        f"- Best training total (2--1, 2-0): **{best_train:,}**\n"
        f"- Holdout day 1 (2-1): **{holdout_profit if holdout_profit is not None else 'N/A'}**\n"
        f"- Full round 2 total: **{full_profit if full_profit is not None else 'N/A'}**\n"
        f"- Daily PnL: day -1={day_m1}, day 0={day_0}, day 1={day_1}\n"
        f"- Best params: {best_params}\n"
        f"- Strategy file: {final_path.name}\n"
    )

    (TRIAL_DIR / "report.md").write_text(
        "# R2 Trial 4 ASH Report\n\n"
        "## Objective\n"
        "Start from trial14, apply mild tuning on R2 days -1 and 0, and test on the held-out R2 day 1 to limit overfitting.\n\n"
        "## Setup\n"
        "- Base strategy: trial14 ASH\n"
        "- Training days: round 2 day -1 and day 0\n"
        "- Holdout day: round 2 day 1\n"
        "- Product: ASH_COATED_OSMIUM only\n"
        "- Tuning style: conservative to moderate changes only\n\n"
        f"Final strategy file: [{final_path.name}]({final_path.name})\n\n"
        "## Results\n"
        f"- Best train PnL (days -1 and 0): **{best_train:,}**\n"
        f"- Holdout day 1 PnL: **{holdout_profit if holdout_profit is not None else 'N/A'}**\n"
        f"- Full round 2 PnL: **{full_profit if full_profit is not None else 'N/A'}**\n\n"
        "### Day-by-day PnL\n"
        "| Day | ASH PnL |\n"
        "|---:|---:|\n"
        f"| -1 | {day_m1 if day_m1 is not None else 'N/A'} |\n"
        f"| 0 | {day_0 if day_0 is not None else 'N/A'} |\n"
        f"| 1 | {day_1 if day_1 is not None else 'N/A'} |\n"
    )

    print("BEST_TRAIN", best_train)
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
