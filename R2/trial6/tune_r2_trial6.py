from pathlib import Path
import itertools
import re
import subprocess


ROOT = Path("/Users/ericlu/Works/imcp4/imcprosp4")
TRIAL_DIR = ROOT / "R2" / "trial6"
TRIAL_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE = '''from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import json
import math

ASH = "ASH_COATED_OSMIUM"
LIMIT = 50


class Trader:
    """R2 Trial 6: ASH profit-max variant tuned on days -1 and 0."""

    def run(self, state: TradingState):
        td = self._load_td(state.traderData)
        result: Dict[str, List[Order]] = {}

        if ASH not in state.order_depths:
            return result, 0, json.dumps(td)

        od = state.order_depths[ASH]
        if not od.buy_orders or not od.sell_orders:
            result[ASH] = []
            return result, 0, json.dumps(td)

        pos = state.position.get(ASH, 0)
        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid
        ts = state.timestamp

        prev_pos = td.get("prev_pos", pos)
        no_fill = td.get("no_fill", 0)
        if pos == prev_pos:
            no_fill = min(80, no_fill + 1)
        else:
            no_fill = 0
        td["prev_pos"] = pos
        td["no_fill"] = no_fill
        participation = min(1.0, no_fill / 20.0)

        ema = __EMA_ALPHA__ * mid + (1.0 - __EMA_ALPHA__) * td.get("ema", mid)
        td["ema"] = ema

        mids = td.get("mid_hist", [])
        mids.append(mid)
        mids = mids[-__HIST_LEN__:]
        td["mid_hist"] = mids

        short = mids[-__SHORT_LEN__:] if len(mids) >= __SHORT_LEN__ else mids
        long = mids[-__LONG_LEN__:] if len(mids) >= __LONG_LEN__ else mids
        short_mean = sum(short) / len(short)
        long_mean = sum(long) / len(long)
        slope = short_mean - long_mean
        z = 0.0 if len(short) < 4 else (mid - short_mean) / max(1e-6, self._std(short))

        wall_bid, wall_ask = self._get_walls(od, __WALL_MIN__)
        wall_mid = 0.5 * (wall_bid + wall_ask)
        imb = self._imbalance(od)

        fair = __WALL_W__ * wall_mid + __EMA_W__ * ema + __TREND_W__ * (0.6 * short_mean + 0.4 * long_mean) + __IMB_W__ * imb

        progress = min(max(ts / 99900.0, 0.0), 1.0)
        bucket = min(9, int(progress * 10))
        target_by_bucket = [__TARGETS__]
        target = target_by_bucket[bucket]
        if slope > __SLOPE_UP_TRIG__:
            target += __SLOPE_UP_ADD__
        elif slope < -__SLOPE_DN_TRIG__:
            target -= __SLOPE_DN_SUB__
        if z <= -__Z_BUY_TRIG__:
            target += __Z_BUY_ADD__
        if z >= __Z_SELL_TRIG__:
            target -= __Z_SELL_SUB__
        target = max(-48.0, min(48.0, target))

        orders: List[Order] = []

        take_width = __TAKE_WIDTH__
        if abs(z) >= __TAKE_Z_TIGHTEN__:
            take_width = 0
        take_cap = __TAKE_CAP_BASE__ + int(__TAKE_CAP_PART__ * participation)

        for ask, vol in sorted(od.sell_orders.items()):
            if ask <= fair - take_width:
                qty = min(-vol, LIMIT - pos, take_cap)
                if qty > 0:
                    orders.append(Order(ASH, ask, qty))
                    pos += qty

        carry_floor = 0
        if progress >= __CARRY_T1__ and slope > __CARRY_S1__:
            carry_floor = __CARRY_F1__
        if progress >= __CARRY_T2__ and slope > __CARRY_S2__:
            carry_floor = max(carry_floor, __CARRY_F2__)

        if (z >= __UNWIND_Z__ and pos > target + __UNWIND_GAP__) or (slope < -__UNWIND_SLOPE__ and pos > target + (__UNWIND_GAP__ + 2)):
            for bid, vol in sorted(od.buy_orders.items(), reverse=True):
                if bid >= fair + 1:
                    qty = min(vol, LIMIT + pos, __UNWIND_CAP__)
                    qty = min(qty, max(0, pos - carry_floor))
                    if qty > 0:
                        orders.append(Order(ASH, bid, -qty))
                        pos -= qty

        inv_ratio = (pos - target) / LIMIT

        base_half = __HALF_LO__ if spread <= __SPREAD_CUTOFF__ else __HALF_HI__
        if participation > 0.6:
            base_half = max(1, base_half - 1)

        bid_px = math.floor(fair - base_half - __INV_SKEW__ * inv_ratio + __SLOPE_PX__ * slope)
        ask_px = math.ceil(fair + base_half - __INV_SKEW__ * inv_ratio + __SLOPE_PX__ * slope)

        if best_bid + __IMPROVE_GAP__ < fair:
            bid_px = max(bid_px, best_bid + 1)
        if best_ask - __IMPROVE_GAP__ > fair:
            ask_px = min(ask_px, best_ask - 1)
        if bid_px >= ask_px:
            bid_px = ask_px - 1

        buy_cap = max(0, LIMIT - pos)
        sell_cap = max(0, LIMIT + pos)

        buy_base = __BUY_BASE__ + int(__BUY_PART__ * participation)
        sell_base = __SELL_BASE__ + int(__SELL_PART__ * participation)
        buy_qty = min(buy_cap, max(1, int(buy_base * (1 - __BUY_INV_W__ * inv_ratio))))
        sell_qty = min(sell_cap, max(1, int(sell_base * (1 + __SELL_INV_W__ * inv_ratio))))

        suppress_sell = (slope > __SUPPRESS_SELL_SLOPE__ and pos < target + __SUPPRESS_SELL_GAP__) or (z <= -__SUPPRESS_SELL_Z__) or (pos <= carry_floor)
        suppress_buy = (slope < -__SUPPRESS_BUY_SLOPE__ and pos > target + __SUPPRESS_BUY_GAP__ and z > __SUPPRESS_BUY_Z__)

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

    def _std(self, xs: List[float]):
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


def day_profit(text: str, day: int) -> int | None:
    m = re.search(rf"Round 2 day {day}:\s*([\-\d,]+)", text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def fill(params: dict[str, object]) -> str:
    code = TEMPLATE
    for k, v in params.items():
        code = code.replace(f"__{k}__", str(v))
    return code


def main() -> None:
    base = {
        "EMA_ALPHA": 0.28,
        "HIST_LEN": 52,
        "SHORT_LEN": 10,
        "LONG_LEN": 26,
        "WALL_MIN": 11,
        "WALL_W": 0.52,
        "EMA_W": 0.28,
        "TREND_W": 0.20,
        "IMB_W": 0.50,
        "TARGETS": "36.0, 36.0, 35.0, 34.0, 32.0, 31.0, 31.0, 37.0, 40.0, 41.0",
        "SLOPE_UP_TRIG": 0.80,
        "SLOPE_DN_TRIG": 0.70,
        "SLOPE_UP_ADD": 4.0,
        "SLOPE_DN_SUB": 2.0,
        "Z_BUY_TRIG": 1.2,
        "Z_SELL_TRIG": 1.8,
        "Z_BUY_ADD": 4.0,
        "Z_SELL_SUB": 3.0,
        "TAKE_WIDTH": 1,
        "TAKE_Z_TIGHTEN": 1.3,
        "TAKE_CAP_BASE": 7,
        "TAKE_CAP_PART": 4,
        "CARRY_T1": 0.42,
        "CARRY_T2": 0.70,
        "CARRY_S1": 0.45,
        "CARRY_S2": 0.65,
        "CARRY_F1": 32,
        "CARRY_F2": 40,
        "UNWIND_Z": 2.4,
        "UNWIND_SLOPE": 0.55,
        "UNWIND_GAP": 6,
        "UNWIND_CAP": 8,
        "HALF_LO": 2,
        "HALF_HI": 3,
        "SPREAD_CUTOFF": 12,
        "INV_SKEW": 4.6,
        "SLOPE_PX": 0.20,
        "IMPROVE_GAP": 1,
        "BUY_BASE": 28,
        "SELL_BASE": 22,
        "BUY_PART": 8,
        "SELL_PART": 4,
        "BUY_INV_W": 1.0,
        "SELL_INV_W": 1.0,
        "SUPPRESS_SELL_SLOPE": 0.65,
        "SUPPRESS_SELL_GAP": 2,
        "SUPPRESS_SELL_Z": 0.65,
        "SUPPRESS_BUY_SLOPE": 1.00,
        "SUPPRESS_BUY_GAP": 8,
        "SUPPRESS_BUY_Z": 0.20,
    }

    grid = list(
        itertools.product(
            [0.26, 0.30, 0.34],   # EMA_ALPHA
            [6, 7, 8],            # TAKE_CAP_BASE
            [4.2, 4.6, 5.0],      # INV_SKEW
            [26, 28, 30],         # BUY_BASE
            [21, 22],             # SELL_BASE
            [38, 40, 42],         # CARRY_F2
        )
    )

    results: list[tuple[int, dict[str, object], Path]] = []

    for i, (ema_alpha, take_cap_base, inv_skew, buy_base, sell_base, carry_f2) in enumerate(grid):
        params = dict(base)
        params["EMA_ALPHA"] = ema_alpha
        params["TAKE_CAP_BASE"] = take_cap_base
        params["INV_SKEW"] = inv_skew
        params["BUY_BASE"] = buy_base
        params["SELL_BASE"] = sell_base
        params["CARRY_F2"] = carry_f2

        cand = TRIAL_DIR / f"_cand_{i:03d}.py"
        cand.write_text(fill(params))

        train, _ = run_bt(cand, ["2--1", "2-0"])
        if train is not None:
            results.append((train, params, cand))
        print(f"candidate {i + 1}/{len(grid)} train={train}")

    if not results:
        raise SystemExit("No successful candidates")

    results.sort(key=lambda x: x[0], reverse=True)
    best_train, best_params, best_cand = results[0]

    holdout, holdout_out = run_bt(best_cand, ["2-1"])
    full, full_out = run_bt(best_cand, ["2--1", "2-0", "2-1"])
    d_m1 = day_profit(full_out, -1)
    d_0 = day_profit(full_out, 0)
    d_1 = day_profit(full_out, 1)

    final_path = TRIAL_DIR / "r2_ash_maxprofit_tuned.py"
    final_path.write_text(best_cand.read_text())
    (TRIAL_DIR / "day1_backtest.log").write_text(holdout_out)
    (TRIAL_DIR / "full_round2_backtest.log").write_text(full_out)

    (TRIAL_DIR / "summary.md").write_text(
        "# R2 Trial 6 - ASH Max-Profit Tuned\n\n"
        "Tuned on round2 days -1 and 0, validated on day 1.\n\n"
        f"- Best training total: **{best_train:,}**\n"
        f"- Holdout day 1: **{holdout if holdout is not None else 'N/A'}**\n"
        f"- Full round 2 total: **{full if full is not None else 'N/A'}**\n"
        f"- Daily PnL: day -1={d_m1}, day 0={d_0}, day 1={d_1}\n"
        f"- Strategy file: {final_path.name}\n"
        f"- Best params: {best_params}\n"
    )

    print("BEST_TRAIN", best_train)
    print("HOLDOUT_DAY1", holdout)
    print("FULL", full)
    print("DAY_M1", d_m1)
    print("DAY_0", d_0)
    print("DAY_1", d_1)
    print("FINAL_FILE", final_path)

    for _, _, cand in results:
        if cand != best_cand and cand.exists():
            cand.unlink()
    if best_cand.exists() and best_cand.name.startswith("_cand_"):
        best_cand.unlink()


if __name__ == "__main__":
    main()
