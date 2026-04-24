#!/usr/bin/env python3
"""
Reverse-engineering utilities for PEPPER price-stream generation.

This script focuses on `prices_round_x_day_y.csv` (order book snapshots), with:
1) Empirical Markov-style generator for plausible synthetic PEPPER streams.
2) Prefix-matching continuation to recover exact future ticks when a prefix is
   from one of the known historical days in this repo.

Notes:
- Producing *identical* unseen future data is generally impossible without the
  true hidden simulator logic/seed.
- Prefix continuation can be identical when the prefix uniquely identifies an
  existing day/window in the known datasets.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

PEPPER = "INTARIAN_PEPPER_ROOT"
BOOK_COLS = [
    "bid_price_1",
    "bid_volume_1",
    "bid_price_2",
    "bid_volume_2",
    "bid_price_3",
    "bid_volume_3",
    "ask_price_1",
    "ask_volume_1",
    "ask_price_2",
    "ask_volume_2",
    "ask_price_3",
    "ask_volume_3",
]
ROW_COLS = ["day", "timestamp", "product", *BOOK_COLS, "mid_price", "profit_and_loss"]


@dataclass(frozen=True)
class DayKey:
    round_id: int
    day: int

    def __str__(self) -> str:
        return f"r{self.round_id}:day{self.day}"


@dataclass
class DaySeries:
    key: DayKey
    df: pd.DataFrame


@dataclass(frozen=True)
class BookTemplate:
    # offsets are measured in half-ticks from mid2 (mid_price * 2)
    bid_levels: Tuple[Tuple[int, int], ...]  # (price_offset2, volume)
    ask_levels: Tuple[Tuple[int, int], ...]  # (price_offset2, volume)


class PepperModel:
    def __init__(self) -> None:
        self.delta_transitions: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        self.delta_by_prev: Dict[int, Counter] = defaultdict(Counter)
        self.delta_global: Counter = Counter()

        self.spread_transitions: Dict[int, Counter] = defaultdict(Counter)
        self.spread_global: Counter = Counter()

        self.templates_by_spread_sign: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
        self.templates_by_spread: Dict[int, Counter] = defaultdict(Counter)

    @staticmethod
    def _weighted_choice(counter: Counter, rng: random.Random):
        if not counter:
            raise ValueError("Cannot sample from empty distribution")
        total = sum(counter.values())
        r = rng.uniform(0, total)
        acc = 0.0
        for k, w in counter.items():
            acc += w
            if acc >= r:
                return k
        return next(iter(counter.keys()))

    @staticmethod
    def _phase_bucket(idx: int, n: int) -> int:
        if n <= 0:
            return 0
        return min(9, int((idx * 10) / n))

    @staticmethod
    def _clip_delta(d: int) -> int:
        return max(-4, min(4, d))

    @staticmethod
    def _book_template(row: pd.Series) -> BookTemplate:
        mid2 = int(round(float(row["mid_price"]) * 2))

        bid_levels: List[Tuple[int, int]] = []
        ask_levels: List[Tuple[int, int]] = []
        for lvl in (1, 2, 3):
            bp = row.get(f"bid_price_{lvl}")
            bv = row.get(f"bid_volume_{lvl}")
            if pd.notna(bp) and pd.notna(bv):
                off2 = int(round(float(bp) * 2)) - mid2
                bid_levels.append((off2, int(float(bv))))

            ap = row.get(f"ask_price_{lvl}")
            av = row.get(f"ask_volume_{lvl}")
            if pd.notna(ap) and pd.notna(av):
                off2 = int(round(float(ap) * 2)) - mid2
                ask_levels.append((off2, int(float(av))))

        return BookTemplate(tuple(bid_levels), tuple(ask_levels))

    @staticmethod
    def _spread(row: pd.Series) -> Optional[int]:
        bp = row.get("bid_price_1")
        ap = row.get("ask_price_1")
        if pd.isna(bp) or pd.isna(ap):
            return None
        return int(round(float(ap) - float(bp)))

    @staticmethod
    def _sign(x: int) -> int:
        return -1 if x < 0 else (1 if x > 0 else 0)

    def fit(self, days: Sequence[DaySeries]) -> None:
        for ds in days:
            d = ds.df.sort_values("timestamp").reset_index(drop=True)
            n = len(d)
            if n < 2:
                continue

            mid2 = (d["mid_price"].astype(float) * 2).round().astype(int).tolist()
            spreads = [self._spread(d.iloc[i]) for i in range(n)]

            deltas = [0]
            deltas.extend(mid2[i] - mid2[i - 1] for i in range(1, n))

            for i in range(1, n):
                prev_d = deltas[i - 1]
                nxt_d = deltas[i]
                prev_sp = spreads[i - 1] if spreads[i - 1] is not None else 0
                phase = self._phase_bucket(i - 1, n)
                ctx = (self._clip_delta(prev_d), prev_sp, phase)

                self.delta_transitions[ctx][nxt_d] += 1
                self.delta_by_prev[self._clip_delta(prev_d)][nxt_d] += 1
                self.delta_global[nxt_d] += 1

                sp_prev = spreads[i - 1]
                sp_now = spreads[i]
                if sp_prev is not None and sp_now is not None:
                    self.spread_transitions[sp_prev][sp_now] += 1
                    self.spread_global[sp_now] += 1

            for i in range(n):
                sp = spreads[i]
                if sp is None:
                    continue
                tmpl = self._book_template(d.iloc[i])
                sgn = self._sign(deltas[i])
                self.templates_by_spread_sign[(sp, sgn)][tmpl] += 1
                self.templates_by_spread[sp][tmpl] += 1

    def sample_next_delta(self, prev_delta: int, prev_spread: int, phase: int, rng: random.Random) -> int:
        ctx = (self._clip_delta(prev_delta), prev_spread, phase)
        if self.delta_transitions.get(ctx):
            return int(self._weighted_choice(self.delta_transitions[ctx], rng))
        if self.delta_by_prev.get(self._clip_delta(prev_delta)):
            return int(self._weighted_choice(self.delta_by_prev[self._clip_delta(prev_delta)], rng))
        return int(self._weighted_choice(self.delta_global, rng))

    def sample_next_spread(self, prev_spread: int, rng: random.Random) -> int:
        if self.spread_transitions.get(prev_spread):
            return int(self._weighted_choice(self.spread_transitions[prev_spread], rng))
        return int(self._weighted_choice(self.spread_global, rng))

    def sample_template(self, spread: int, delta_sign: int, rng: random.Random) -> BookTemplate:
        key = (spread, delta_sign)
        if self.templates_by_spread_sign.get(key):
            return self._weighted_choice(self.templates_by_spread_sign[key], rng)
        if self.templates_by_spread.get(spread):
            return self._weighted_choice(self.templates_by_spread[spread], rng)

        # Last fallback: any template at all.
        all_templates = Counter()
        for counter in self.templates_by_spread.values():
            all_templates.update(counter)
        if not all_templates:
            raise ValueError("No templates fitted")
        return self._weighted_choice(all_templates, rng)


def discover_price_files(repo_root: Path) -> List[Tuple[int, Path]]:
    files: List[Tuple[int, Path]] = []
    for p in sorted((repo_root / "R1" / "data").glob("prices_round_1_day_*.csv")):
        files.append((1, p))
    for p in sorted((repo_root / "R2" / "data2").glob("prices_round_2_day_*.csv")):
        files.append((2, p))
    return files


def load_pepper_days(repo_root: Path) -> List[DaySeries]:
    days: List[DaySeries] = []
    for round_id, fp in discover_price_files(repo_root):
        df = pd.read_csv(fp, sep=";")
        p = df[df["product"] == PEPPER].copy()
        if p.empty:
            continue

        day_val = int(p["day"].iloc[0])
        p = p.sort_values("timestamp").reset_index(drop=True)

        # Keep only expected columns and normalize numerics.
        for c in ROW_COLS:
            if c not in p.columns:
                p[c] = math.nan
        p = p[ROW_COLS].copy()

        num_cols = [c for c in ROW_COLS if c not in ("product",)]
        for c in num_cols:
            p[c] = pd.to_numeric(p[c], errors="coerce")
        p["product"] = PEPPER

        days.append(DaySeries(DayKey(round_id=round_id, day=day_val), p))

    if not days:
        raise FileNotFoundError("No PEPPER price files found under R1/data and R2/data2")
    return days


def summarize(days: Sequence[DaySeries]) -> pd.DataFrame:
    rows = []
    for ds in days:
        d = ds.df
        spread = d["ask_price_1"] - d["bid_price_1"]
        mid = d["mid_price"]
        mid2 = (mid.astype(float) * 2).round().astype(int)
        deltas = mid2.diff().fillna(0)

        rows.append(
            {
                "series": str(ds.key),
                "rows": len(d),
                "mid_min": float(mid.min()),
                "mid_max": float(mid.max()),
                "spread_mode": float(spread.mode().iloc[0]) if spread.notna().any() else math.nan,
                "spread_mean": float(spread.mean()) if spread.notna().any() else math.nan,
                "delta2_mode": int(deltas.mode().iloc[0]),
                "delta2_std": float(deltas.std(ddof=0)),
            }
        )

    return pd.DataFrame(rows)


def _to_price(x2: int) -> float:
    return x2 / 2.0


def _int_or_nan(x: Optional[float]):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    if abs(x - round(x)) < 1e-9:
        return int(round(x))
    return float(x)


def generate_synthetic(
    model: PepperModel,
    reference_day: DaySeries,
    n_steps: int,
    seed: int,
    out_path: Path,
) -> None:
    rng = random.Random(seed)
    ref = reference_day.df.sort_values("timestamp").reset_index(drop=True)
    if ref.empty:
        raise ValueError("Reference day is empty")

    first = ref.iloc[0].copy()
    first_mid2 = int(round(float(first["mid_price"]) * 2))

    # Derive initial spread from row or fallback to mode.
    sp0 = first.get("ask_price_1") - first.get("bid_price_1")
    if pd.isna(sp0):
        sp0 = max(model.spread_global, key=model.spread_global.get)
    sp0 = int(round(float(sp0)))

    rows: List[dict] = []
    cur_mid2 = first_mid2
    cur_spread = sp0
    prev_delta = 0
    ts0 = int(first["timestamp"])

    for i in range(n_steps):
        if i > 0:
            phase = min(9, int((i * 10) / max(1, n_steps)))
            d2 = model.sample_next_delta(prev_delta=prev_delta, prev_spread=cur_spread, phase=phase, rng=rng)
            cur_mid2 += d2
            prev_delta = d2
            cur_spread = model.sample_next_spread(cur_spread, rng)

        tmpl = model.sample_template(cur_spread, -1 if prev_delta < 0 else (1 if prev_delta > 0 else 0), rng)

        out = {
            "day": int(reference_day.key.day),
            "timestamp": ts0 + 100 * i,
            "product": PEPPER,
            "bid_price_1": "",
            "bid_volume_1": "",
            "bid_price_2": "",
            "bid_volume_2": "",
            "bid_price_3": "",
            "bid_volume_3": "",
            "ask_price_1": "",
            "ask_volume_1": "",
            "ask_price_2": "",
            "ask_volume_2": "",
            "ask_price_3": "",
            "ask_volume_3": "",
            "mid_price": _to_price(cur_mid2),
            "profit_and_loss": 0.0,
        }

        for lvl, (off2, vol) in enumerate(tmpl.bid_levels, start=1):
            if lvl > 3:
                break
            out[f"bid_price_{lvl}"] = _int_or_nan(_to_price(cur_mid2 + off2))
            out[f"bid_volume_{lvl}"] = int(vol)

        for lvl, (off2, vol) in enumerate(tmpl.ask_levels, start=1):
            if lvl > 3:
                break
            out[f"ask_price_{lvl}"] = _int_or_nan(_to_price(cur_mid2 + off2))
            out[f"ask_volume_{lvl}"] = int(vol)

        rows.append(out)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ROW_COLS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _rows_match(prefix: pd.DataFrame, candidate: pd.DataFrame, start_idx: int, tol: float = 1e-9) -> bool:
    if start_idx < 0 or start_idx + len(prefix) > len(candidate):
        return False

    cand = candidate.iloc[start_idx : start_idx + len(prefix)].reset_index(drop=True)

    compare_cols = ["timestamp", *BOOK_COLS, "mid_price"]
    for i in range(len(prefix)):
        for c in compare_cols:
            pv = prefix.iloc[i].get(c)
            cv = cand.iloc[i].get(c)
            if pd.isna(pv):
                continue
            if pd.isna(cv):
                return False
            if isinstance(pv, float) or isinstance(cv, float):
                if abs(float(pv) - float(cv)) > tol:
                    return False
            else:
                if int(pv) != int(cv):
                    return False
    return True


def continue_from_prefix(days: Sequence[DaySeries], prefix_csv: Path, n_future: int, out_path: Path) -> Tuple[DayKey, int]:
    pref = pd.read_csv(prefix_csv, sep=";")
    pref = pref[pref["product"] == PEPPER].copy()
    if pref.empty:
        raise ValueError("Prefix CSV contains no PEPPER rows")
    pref = pref.sort_values("timestamp").reset_index(drop=True)

    # Ensure known columns exist.
    for c in ["timestamp", *BOOK_COLS, "mid_price"]:
        if c not in pref.columns:
            pref[c] = math.nan

    matches: List[Tuple[DayKey, int]] = []
    for ds in days:
        cand = ds.df.sort_values("timestamp").reset_index(drop=True)
        for i in range(max(0, len(cand) - len(pref) + 1)):
            if _rows_match(pref, cand, i):
                matches.append((ds.key, i))

    if not matches:
        raise ValueError("No exact prefix match found in known R1/R2 PEPPER price series")

    # Pick the earliest deterministic match; if multiple, this remains reproducible.
    matches.sort(key=lambda x: (x[0].round_id, x[0].day, x[1]))
    key, start = matches[0]

    series = next(ds.df for ds in days if ds.key == key).sort_values("timestamp").reset_index(drop=True)
    begin = start + len(pref)
    end = min(len(series), begin + n_future)
    fut = series.iloc[begin:end].copy()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fut.to_csv(out_path, sep=";", index=False)
    return key, start


def pick_day(days: Sequence[DaySeries], key_str: str) -> DaySeries:
    # Format: r1:day-1
    s = key_str.strip().lower()
    if not s.startswith("r") or ":day" not in s:
        raise ValueError("reference-day must look like r1:day-1")
    left, right = s.split(":day", 1)
    round_id = int(left[1:])
    day = int(right)

    for ds in days:
        if ds.key.round_id == round_id and ds.key.day == day:
            return ds
    known = ", ".join(str(ds.key) for ds in days)
    raise ValueError(f"Unknown day key {key_str}. Known: {known}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reverse-engineering helper for PEPPER prices_round datasets")
    parser.add_argument("--repo-root", default=".", help="Path to repository root (default: .)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sum = sub.add_parser("summary", help="Show per-day summary stats for PEPPER price streams")

    p_gen = sub.add_parser("generate", help="Generate synthetic PEPPER stream from fitted empirical model")
    p_gen.add_argument("--reference-day", required=True, help="Example: r1:day-1")
    p_gen.add_argument("--steps", type=int, default=1000, help="Number of ticks to generate")
    p_gen.add_argument("--seed", type=int, default=42, help="RNG seed")
    p_gen.add_argument("--out", required=True, help="Output CSV path")

    p_pred = sub.add_parser("predict", help="Continue future ticks from a known prefix (exact match)")
    p_pred.add_argument("--prefix", required=True, help="CSV containing prefix rows for PEPPER")
    p_pred.add_argument("--future", type=int, default=200, help="How many future rows to emit")
    p_pred.add_argument("--out", required=True, help="Output CSV path")

    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    days = load_pepper_days(repo_root)

    model = PepperModel()
    model.fit(days)

    if args.cmd == "summary":
        df = summarize(days)
        with pd.option_context("display.max_columns", None, "display.width", 180):
            print(df.to_string(index=False))
        print("\nKnown day keys:")
        for ds in days:
            print(f"- {ds.key}")
        return

    if args.cmd == "generate":
        ref = pick_day(days, args.reference_day)
        out = Path(args.out)
        generate_synthetic(model=model, reference_day=ref, n_steps=args.steps, seed=args.seed, out_path=out)
        print(f"Wrote synthetic PEPPER stream to {out}")
        return

    if args.cmd == "predict":
        out = Path(args.out)
        key, start = continue_from_prefix(days, Path(args.prefix), args.future, out)
        print(f"Matched prefix to {key} at row index {start}; wrote continuation to {out}")
        return


if __name__ == "__main__":
    main()
