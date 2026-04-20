from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PEPPER = "INTARIAN_PEPPER_ROOT"

TRIAL_LOGS = {
    "trial23": ROOT / "trial23" / "backtest_round1.log",
    "trial33": ROOT / "trial33" / "backtest_round1.log",
}

OUT_PATH = ROOT / "erick" / "backtest_reports" / "pepper_trials_23_33_log_analysis.md"


@dataclass
class TrialMetrics:
    trial: str
    total_pnl: float
    best_day: float
    worst_day: float
    day_std: float
    avg_day_max_dd: float
    worst_day_max_dd: float
    avg_step_std: float
    avg_positive_step_ratio: float


def extract_activities_csv_text(log_text: str) -> str:
    marker = "Activities log:\n"
    start = log_text.find(marker)
    if start == -1:
        raise ValueError("Activities log section not found")

    section = log_text[start + len(marker) :]
    lines = section.splitlines()
    kept: list[str] = []

    for line in lines:
        s = line.strip()
        if not s:
            break
        if s.startswith("Trade History:"):
            break
        if ";" not in s:
            continue
        kept.append(s)

    if not kept:
        raise ValueError("No CSV lines found in Activities log section")

    return "\n".join(kept)


def load_pepper_df(log_path: Path) -> pd.DataFrame:
    text = log_path.read_text(encoding="utf-8")
    csv_text = extract_activities_csv_text(text)
    df = pd.read_csv(StringIO(csv_text), sep=";")

    df = df[df["product"] == PEPPER].copy()
    df["day"] = pd.to_numeric(df["day"], errors="coerce")
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["profit_and_loss"] = pd.to_numeric(df["profit_and_loss"], errors="coerce")

    df = df.dropna(subset=["day", "timestamp", "profit_and_loss"])
    df = df.sort_values(["day", "timestamp"]).reset_index(drop=True)

    return df


def compute_trial_metrics(trial: str, df: pd.DataFrame) -> tuple[TrialMetrics, pd.DataFrame, pd.DataFrame]:
    day_end = (
        df.groupby("day", as_index=False)
        .agg(day_pnl=("profit_and_loss", "last"))
        .sort_values("day")
        .reset_index(drop=True)
    )

    dd_rows = []
    step_std_rows = []
    pos_ratio_rows = []
    for day, sub in df.groupby("day"):
        s = sub["profit_and_loss"].reset_index(drop=True)
        run_max = s.cummax()
        dd = run_max - s
        dd_rows.append({"day": day, "day_max_dd": float(dd.max())})

        steps = s.diff().fillna(0.0)
        step_std_rows.append(float(steps.std(ddof=0)))
        pos_ratio_rows.append(float((steps > 0).mean()))

    dd_df = pd.DataFrame(dd_rows).sort_values("day").reset_index(drop=True)

    metrics = TrialMetrics(
        trial=trial,
        total_pnl=float(day_end["day_pnl"].sum()),
        best_day=float(day_end["day_pnl"].max()),
        worst_day=float(day_end["day_pnl"].min()),
        day_std=float(day_end["day_pnl"].std(ddof=0)),
        avg_day_max_dd=float(dd_df["day_max_dd"].mean()),
        worst_day_max_dd=float(dd_df["day_max_dd"].max()),
        avg_step_std=float(sum(step_std_rows) / len(step_std_rows)),
        avg_positive_step_ratio=float(sum(pos_ratio_rows) / len(pos_ratio_rows)),
    )

    # Bucket PnL contributions by day and then averaged over days.
    bucket_df = df.copy()
    bucket_df["bucket"] = (bucket_df["timestamp"] // 10000).clip(0, 9).astype(int)
    bucket_end = (
        bucket_df.groupby(["day", "bucket"], as_index=False)
        .agg(bucket_end_pnl=("profit_and_loss", "last"))
        .sort_values(["day", "bucket"])
    )
    bucket_end["bucket_start_pnl"] = bucket_end.groupby("day")["bucket_end_pnl"].shift(1).fillna(0.0)
    bucket_end["bucket_pnl"] = bucket_end["bucket_end_pnl"] - bucket_end["bucket_start_pnl"]

    bucket_mean = (
        bucket_end.groupby("bucket", as_index=False)
        .agg(bucket_pnl=("bucket_pnl", "mean"))
        .sort_values("bucket")
        .reset_index(drop=True)
    )

    day_dd = dd_df.copy()
    day_dd.insert(0, "trial", trial)

    return metrics, day_end, bucket_mean, day_dd


def fmt_num(x: float) -> str:
    return f"{x:,.1f}" if abs(x - round(x)) > 1e-9 else f"{x:,.0f}"


def main() -> None:
    metric_rows: list[TrialMetrics] = []
    day_frames = []
    bucket_frames = []
    day_dd_frames = []

    for trial, path in TRIAL_LOGS.items():
        df = load_pepper_df(path)
        metrics, day_end, bucket_mean, day_dd = compute_trial_metrics(trial, df)

        metric_rows.append(metrics)

        d = day_end.copy()
        d.insert(0, "trial", trial)
        day_frames.append(d)

        b = bucket_mean.copy()
        b.insert(0, "trial", trial)
        bucket_frames.append(b)

        day_dd_frames.append(day_dd)

    metrics_df = pd.DataFrame([m.__dict__ for m in metric_rows]).sort_values("total_pnl", ascending=False)
    day_df = pd.concat(day_frames, ignore_index=True).sort_values(["day", "day_pnl"], ascending=[True, False])
    day_df["day_rank"] = day_df.groupby("day")["day_pnl"].rank(method="min", ascending=False).astype(int)

    bucket_long = pd.concat(bucket_frames, ignore_index=True)
    bucket_pivot = bucket_long.pivot(index="trial", columns="bucket", values="bucket_pnl").sort_index()
    day_dd_long = pd.concat(day_dd_frames, ignore_index=True).sort_values(["day", "day_max_dd"], ascending=[True, False])

    t33 = bucket_long[bucket_long["trial"] == "trial33"][["bucket", "bucket_pnl"]].rename(columns={"bucket_pnl": "trial33_bucket_pnl"})
    t23 = bucket_long[bucket_long["trial"] == "trial23"][["bucket", "bucket_pnl"]].rename(columns={"bucket_pnl": "trial23_bucket_pnl"})
    bucket_delta = t33.merge(t23, on="bucket", how="inner")
    bucket_delta["delta_33_minus_23"] = bucket_delta["trial33_bucket_pnl"] - bucket_delta["trial23_bucket_pnl"]
    bucket_delta = bucket_delta.sort_values("bucket")

    # Pretty formatting for markdown tables.
    m = metrics_df.copy()
    for col in [
        "total_pnl",
        "best_day",
        "worst_day",
        "day_std",
        "avg_day_max_dd",
        "worst_day_max_dd",
        "avg_step_std",
        "avg_positive_step_ratio",
    ]:
        m[col] = m[col].map(fmt_num)

    d = day_df.copy()
    d["day_pnl"] = d["day_pnl"].map(fmt_num)

    bp = bucket_pivot.copy()
    for col in bp.columns:
        bp[col] = bp[col].map(fmt_num)

    bd = bucket_delta.copy()
    for col in ["trial33_bucket_pnl", "trial23_bucket_pnl", "delta_33_minus_23"]:
        bd[col] = bd[col].map(fmt_num)

    dd = day_dd_long.copy()
    dd["day_max_dd"] = dd["day_max_dd"].map(fmt_num)

    lines: list[str] = []
    lines.append("# PEPPER Log Analysis: Trials 23 vs 33")
    lines.append("")
    lines.append("Method:")
    lines.append("- Parsed `Activities log` from each trial's `backtest_round1.log`.")
    lines.append("- Used PEPPER rows only (`INTARIAN_PEPPER_ROOT`).")
    lines.append("- Bucket PnL computed from bucket-end PnL deltas; table reports mean bucket PnL across days.")
    lines.append("")
    lines.append("## PEPPER total/day summary")
    lines.append(m.to_markdown(index=False))
    lines.append("")
    lines.append("## Day ranking")
    lines.append(d.to_markdown(index=False))
    lines.append("")
    lines.append("## Per-day max drawdown (abs)")
    lines.append(dd.to_markdown(index=False))
    lines.append("")
    lines.append("## Intraday bucket PnL mean by trial (0 early -> 9 late)")
    lines.append(bp.to_markdown())
    lines.append("")
    lines.append("## Bucket delta (trial33 - trial23)")
    lines.append(bd.to_markdown(index=False))

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
