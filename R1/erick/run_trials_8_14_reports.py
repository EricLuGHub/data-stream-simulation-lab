from __future__ import annotations

from io import StringIO
from pathlib import Path
import re
import subprocess

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
R1_DIR = ROOT / "R1"
REPORT_DIR = R1_DIR / "erick" / "backtest_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TRIAL_FILES = {
    "trial8": R1_DIR / "trial8" / "124803.py",
    "trial9": R1_DIR / "trial9" / "124904.py",
    "trial10": R1_DIR / "trial10" / "125001.py",
    "trial11": R1_DIR / "trial11" / "125102.py",
    "trial12": R1_DIR / "trial12" / "125203.py",
    "trial13": R1_DIR / "trial13" / "125304.py",
    "trial14": R1_DIR / "trial14" / "125405.py",
}

DAY_OFFSET = 3_000_000


def _to_markdown_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    lines = [header, sep]
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            val = row[col]
            if isinstance(val, float):
                vals.append(f"{val:.6g}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def _run_backtest(algorithm_path: Path, out_log_path: Path) -> None:
    cmd = [
        str(ROOT / ".venv" / "bin" / "prosperity4btest"),
        str(algorithm_path.relative_to(ROOT)),
        "1",
        "--out",
        str(out_log_path.relative_to(ROOT)),
        "--no-progress",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def _parse_activities(log_path: Path) -> pd.DataFrame:
    lines = log_path.read_text().splitlines()
    start = lines.index("Activities log:") + 1

    header = None
    rows: list[str] = []
    row_re = re.compile(r"^-?\d+;")

    for line in lines[start:]:
        s = line.strip()
        if not s:
            if header is not None:
                break
            continue
        if header is None:
            if s.startswith("day;timestamp;"):
                header = s
            continue
        if row_re.match(s):
            rows.append(s)
        else:
            break

    if header is None or not rows:
        raise ValueError(f"Could not parse activities from {log_path}")

    df = pd.read_csv(StringIO("\n".join([header, *rows])), sep=";")
    df = df.replace("", np.nan)

    numeric_cols = [
        "day",
        "timestamp",
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
        "mid_price",
        "profit_and_loss",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _compute_report_stats(trial_name: str, trial_file: Path, log_file: Path, activities: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    day_order = {day: idx for idx, day in enumerate(sorted(activities["day"].dropna().unique()))}

    total = (
        activities.groupby(["day", "timestamp"], as_index=False)["profit_and_loss"]
        .sum()
        .sort_values(["day", "timestamp"])
        .reset_index(drop=True)
    )
    total["plot_ts"] = total["day"].map(day_order) * DAY_OFFSET + total["timestamp"]
    total["running_max"] = total["profit_and_loss"].cummax()
    total["drawdown"] = total["running_max"] - total["profit_and_loss"]

    final_profit = float(total["profit_and_loss"].iloc[-1]) if len(total) else np.nan
    peak_profit = float(total["profit_and_loss"].max()) if len(total) else np.nan
    valley_profit = float(total["profit_and_loss"].min()) if len(total) else np.nan
    graph_drawdown = float(total["drawdown"].max()) if len(total) else np.nan
    breakeven = total.loc[total["profit_and_loss"] > 0, "plot_ts"] if len(total) else pd.Series([], dtype=float)
    breakeven_ts = float(breakeven.iloc[0]) if len(breakeven) else np.nan

    ash = activities[activities["product"] == "ASH_COATED_OSMIUM"].copy()
    ash = ash[ash["mid_price"].notna()].copy()
    ash = ash[(ash["mid_price"] > 0) & (ash["bid_price_1"] > 0) & (ash["ask_price_1"] > 0)].copy()
    ash["spread"] = ash["ask_price_1"] - ash["bid_price_1"]
    ash["top_depth"] = ash[["bid_volume_1", "ask_volume_1"]].min(axis=1)
    ash["plot_ts"] = ash["day"].map(day_order) * DAY_OFFSET + ash["timestamp"]

    summary = pd.DataFrame(
        [
            {
                "trial": trial_name,
                "algorithm": str(trial_file.relative_to(ROOT)),
                "log": str(log_file.relative_to(ROOT)),
                "round": 1,
                "final_profit": final_profit,
                "graph_peak": peak_profit,
                "graph_valley": valley_profit,
                "graph_drawdown": graph_drawdown,
                "breakeven_timestamp": breakeven_ts,
                "ash_rows": int(len(ash)),
                "ash_days": int(ash["day"].nunique()) if len(ash) else 0,
                "ash_mid_first": float(ash["mid_price"].iloc[0]) if len(ash) else np.nan,
                "ash_mid_last": float(ash["mid_price"].iloc[-1]) if len(ash) else np.nan,
                "ash_spread_mean": float(ash["spread"].mean()) if len(ash) else np.nan,
                "ash_spread_median": float(ash["spread"].median()) if len(ash) else np.nan,
                "ash_top_depth_mean": float(ash["top_depth"].mean()) if len(ash) else np.nan,
            }
        ]
    )

    product_summary = (
        activities.sort_values(["product", "day", "timestamp"])
        .groupby("product", as_index=False)
        .agg(
            final_profit=("profit_and_loss", "last"),
            peak_profit=("profit_and_loss", "max"),
            valley_profit=("profit_and_loss", "min"),
        )
    )

    return summary, product_summary, ash


def _save_plot(trial_name: str, total: pd.DataFrame, ash: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    axes[0].plot(total["plot_ts"], total["profit_and_loss"], color="black", linewidth=1.5)
    axes[0].set_title(f"{trial_name}: total PnL path")
    axes[0].set_ylabel("PnL")

    axes[1].plot(ash["plot_ts"], ash["mid_price"], label="ASH mid", color="tab:blue", linewidth=1.2)
    spread_ax = axes[1].twinx()
    spread_ax.plot(ash["plot_ts"], ash["spread"], label="Top spread", color="tab:orange", alpha=0.7)
    axes[1].set_title(f"{trial_name}: ASH mid and top spread")
    axes[1].set_xlabel("timestamp")
    axes[1].set_ylabel("ASH mid")
    spread_ax.set_ylabel("spread")

    lines = axes[1].lines + spread_ax.lines
    labels = [line.get_label() for line in lines]
    axes[1].legend(lines, labels, loc="upper right")

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    all_summary = []

    for trial_name, trial_file in TRIAL_FILES.items():
        log_file = REPORT_DIR / f"{trial_name}_backtest.log"
        report_csv = REPORT_DIR / f"{trial_name}_backtest_report.csv"
        report_md = REPORT_DIR / f"{trial_name}_backtest_report.md"
        report_png = REPORT_DIR / f"{trial_name}_backtest_report.png"

        _run_backtest(trial_file, log_file)
        activities = _parse_activities(log_file)

        day_order = {day: idx for idx, day in enumerate(sorted(activities["day"].dropna().unique()))}
        total = (
            activities.groupby(["day", "timestamp"], as_index=False)["profit_and_loss"]
            .sum()
            .sort_values(["day", "timestamp"])
            .reset_index(drop=True)
        )
        total["plot_ts"] = total["day"].map(day_order) * DAY_OFFSET + total["timestamp"]

        summary, product_summary, ash = _compute_report_stats(trial_name, trial_file, log_file, activities)
        summary.to_csv(report_csv, index=False)

        md_lines = [
            f"# Backtest Log Report: {trial_name}",
            "",
            f"- Source algorithm: `{trial_file.relative_to(ROOT)}`",
            f"- Source log: `{log_file.relative_to(ROOT)}`",
            f"- Final profit: {summary.iloc[0]['final_profit']:.2f}",
            f"- Graph peak: {summary.iloc[0]['graph_peak']:.2f}",
            f"- Graph valley: {summary.iloc[0]['graph_valley']:.2f}",
            f"- Graph drawdown: {summary.iloc[0]['graph_drawdown']:.2f}",
            "",
            "## Summary Table",
            "",
            _to_markdown_table(summary),
            "",
            "## Product Summary",
            "",
            _to_markdown_table(product_summary),
        ]
        report_md.write_text("\n".join(md_lines))

        _save_plot(trial_name, total, ash, report_png)
        all_summary.append(summary.iloc[0].to_dict())
        print(f"Generated reports for {trial_name}")

    all_df = pd.DataFrame(all_summary).sort_values("final_profit", ascending=False)
    all_df.to_csv(REPORT_DIR / "trials8_14_backtest_report_summary.csv", index=False)
    (REPORT_DIR / "trials8_14_backtest_report_summary.md").write_text(
        "# Trials 8-14 Summary\n\n" + _to_markdown_table(all_df)
    )

    print(f"Done. Reports written to {REPORT_DIR}")


if __name__ == "__main__":
    main()
