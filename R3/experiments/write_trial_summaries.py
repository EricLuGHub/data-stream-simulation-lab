from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TRIALS_DIR = ROOT / "R3" / "trials"
RESULTS_DIR = ROOT / "R3" / "experiments" / "results"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def _load_metadata(trial_dir: Path) -> dict[str, Any]:
    path = trial_dir / "metadata.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _strategy_notes(row: dict[str, Any], meta: dict[str, Any], overall_rank: int, set_rank: int) -> list[str]:
    notes: list[str] = []
    set_name = row.get("set", "UNKNOWN")
    family = row.get("family", "unknown")
    total_pnl = _safe_float(row.get("total_pnl"))
    max_dd = _safe_float(row.get("max_drawdown"))
    d0 = _safe_float(row.get("day_0_pnl"))
    d1 = _safe_float(row.get("day_1_pnl"))

    if set_name == "PACK_ONLY":
        notes.append("This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.")
        if total_pnl > 8000:
            notes.append("Strong initial finding: this parameterization is one of the better PACK candidates and is worth carrying to refinement.")
        elif total_pnl > 5000:
            notes.append("Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.")
        elif total_pnl > 0:
            notes.append("Mixed finding: strategy is profitable but weaker than top PACK variants; likely needs threshold/inventory tuning.")
        else:
            notes.append("Negative finding: strategy underperformed and should not be promoted without significant redesign.")

        if max_dd > 15000:
            notes.append("Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.")
        elif max_dd < 10000:
            notes.append("Risk finding: drawdown is controlled relative to peers, suggesting good inventory discipline.")

    elif set_name == "VELV_VEV_TARGET":
        notes.append("This is a VELV/VEV option-smile strategy using Black-Scholes fair values with strike-level controls.")
        if total_pnl > 10000:
            notes.append("Positive finding: this variant has the strongest voucher-set PnL among current runs and should be prioritized for second-stage tuning.")
        elif total_pnl > 0:
            notes.append("Positive but modest finding: profitable setup, likely sensitive to edge and tau/sigma scaling parameters.")
        elif total_pnl > -50000:
            notes.append("Mixed finding: losses are contained compared with most voucher variants, suggesting promising structure but poor edge calibration.")
        else:
            notes.append("Negative finding: substantial losses suggest over-aggressive cross/quote behavior or mis-calibrated smile assumptions.")

        if d0 > 0 and d1 > 0:
            notes.append("Generalization finding: both day 0 and day 1 were positive, indicating better split robustness.")
        elif d0 * d1 < 0:
            notes.append("Generalization finding: day-level sign flip indicates regime sensitivity and weaker robustness.")
        else:
            notes.append("Generalization finding: losses on both days indicate this configuration is not robust enough to keep.")

    notes.append(f"Relative placement: overall rank #{overall_rank} and set rank #{set_rank} in the evaluated leaderboard.")

    params = meta.get("params", {})
    if params:
        if set_name == "PACK_ONLY":
            notes.append(
                "Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs."
            )
        else:
            notes.append(
                "Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs."
            )

    return notes


def _render_summary(trial: int, row: dict[str, Any], meta: dict[str, Any], overall_rank: int, set_rank: int) -> str:
    set_name = row.get("set", "UNKNOWN")
    family = row.get("family", "unknown")
    status = row.get("status", "unknown")
    raw_err = row.get("error")
    if raw_err is None or (isinstance(raw_err, float) and pd.isna(raw_err)):
        err = ""
    else:
        err = str(raw_err).strip()

    lines = [
        f"# Trial {trial} Summary",
        "",
        "## Strategy",
        "",
        f"- Set: {set_name}",
        f"- Family: {family}",
        f"- Status: {status}",
        f"- Overall rank: {overall_rank}",
        f"- Set rank: {set_rank}",
        "",
        "## PnL Metrics",
        "",
        f"- Total PnL (days 0+1): {_safe_float(row.get('total_pnl')):.2f}",
        f"- Day 0 PnL: {_safe_float(row.get('day_0_pnl')):.2f}",
        f"- Day 1 PnL: {_safe_float(row.get('day_1_pnl')):.2f}",
        f"- Max drawdown proxy: {_safe_float(row.get('max_drawdown')):.2f}",
        f"- Score used for ranking: {_safe_float(row.get('score')):.2f}",
        f"- Curve step volatility: {_safe_float(row.get('curve_step_std')):.2f}",
        "",
        "## Strategy Parameters",
        "",
    ]

    params = meta.get("params", {})
    if params:
        for key in sorted(params.keys()):
            lines.append(f"- {key}: {params[key]}")
    else:
        lines.append("- Metadata parameters unavailable for this trial.")

    lines.extend([
        "",
        "## Notes And Findings",
        "",
    ])

    for n in _strategy_notes(row, meta, overall_rank, set_rank):
        lines.append(f"- {n}")

    if err:
        lines.extend([
            "",
            "## Error Context",
            "",
            f"- {err}",
        ])

    lines.extend([
        "",
        "## Next Action",
        "",
        "- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.",
    ])

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-trial markdown summaries from a leaderboard CSV.")
    parser.add_argument("--leaderboard", type=str, default="leaderboard_day_0_1.csv")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=80)
    parser.add_argument("--filename", type=str, default="summary.md")
    args = parser.parse_args()

    lb_path = RESULTS_DIR / args.leaderboard
    if not lb_path.exists():
        raise FileNotFoundError(f"Leaderboard file not found: {lb_path}")

    df = pd.read_csv(lb_path)
    if "trial" not in df.columns:
        raise ValueError("Leaderboard missing required 'trial' column")

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    overall_rank = {int(t): i + 1 for i, t in enumerate(df["trial"].tolist())}

    set_rank: dict[tuple[str, int], int] = {}
    for set_name in sorted(df["set"].dropna().unique().tolist()):
        sdf = df[df["set"] == set_name].sort_values("score", ascending=False).reset_index(drop=True)
        for i, t in enumerate(sdf["trial"].tolist()):
            set_rank[(set_name, int(t))] = i + 1

    trials_written = 0
    for trial in range(args.start, args.end + 1):
        trial_dir = TRIALS_DIR / f"trial{trial}"
        if not trial_dir.exists():
            continue

        row_df = df[df["trial"] == trial]
        if row_df.empty:
            # Fall back to minimal summary when trial is missing from leaderboard.
            content = "\n".join(
                [
                    f"# Trial {trial} Summary",
                    "",
                    "## Notes",
                    "",
                    "- No leaderboard row found for this trial in the selected results file.",
                ]
            ) + "\n"
        else:
            row = row_df.iloc[0].to_dict()
            meta = _load_metadata(trial_dir)
            o_rank = overall_rank.get(trial, -1)
            s_rank = set_rank.get((str(row.get("set", "UNKNOWN")), trial), -1)
            content = _render_summary(trial, row, meta, o_rank, s_rank)

        out_file = trial_dir / args.filename
        out_file.write_text(content)
        trials_written += 1

    print(f"Wrote {args.filename} for {trials_written} trials using {lb_path.name}")


if __name__ == "__main__":
    main()
