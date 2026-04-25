from __future__ import annotations

import argparse
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TRIALS_DIR = ROOT / "R3" / "trials"
RESULTS_DIR = ROOT / "R3" / "experiments" / "results"
DATA_ROOT = ROOT / "codex_research" / "backtest_data"
MANIFEST = ROOT / "R3" / "experiments" / "trial_manifest.json"


def build_cmd(trader_file: Path, days: list[int], out_file: Path) -> list[str]:
    targets = [f"3-{d}" for d in days]
    exe = "prosperity4btest"
    cmd = [
        exe,
        "cli",
        str(trader_file),
        *targets,
        "--data",
        str(DATA_ROOT),
        "--no-progress",
        "--out",
        str(out_file),
    ]
    return cmd


def run_backtest(trader_file: Path, days: list[int], out_file: Path, timeout: int) -> tuple[bool, str]:
    cmd = build_cmd(trader_file, days, out_file)
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        fallback = ROOT / ".venv" / "bin" / "prosperity4btest"
        cmd[0] = str(fallback)
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).strip()
        if len(msg) > 800:
            msg = msg[:800] + "..."
        return False, msg or f"returncode={proc.returncode}"
    return True, ""


def _extract_activities_csv(raw: str) -> str:
    marker = "Activities log:\n"
    pos = raw.find(marker)
    if pos < 0:
        return ""
    body = raw[pos + len(marker) :]
    cut_markers = ["\n\nTrade History:", "\n\nSandbox logs:", "\n\nGraph log:"]
    end = len(body)
    for m in cut_markers:
        i = body.find(m)
        if i >= 0:
            end = min(end, i)
    return body[:end].strip()


def parse_metrics(log_file: Path) -> dict[str, float]:
    raw = log_file.read_text()
    csv_blob = _extract_activities_csv(raw)
    if not csv_blob:
        return {
            "total_pnl": -1e12,
            "max_drawdown": 1e12,
            "score": -1e12,
            "curve_std": 1e12,
            "curve_step_std": 1e12,
        }

    df = pd.read_csv(StringIO(csv_blob), sep=";")
    if df.empty or "profit_and_loss" not in df.columns:
        return {
            "total_pnl": -1e12,
            "max_drawdown": 1e12,
            "score": -1e12,
            "curve_std": 1e12,
            "curve_step_std": 1e12,
        }

    df["profit_and_loss"] = pd.to_numeric(df["profit_and_loss"], errors="coerce").fillna(0.0)

    curve_parts = []
    day_totals = {}
    offset = 0.0
    for day in sorted(df["day"].unique()):
        d = df[df["day"] == day]
        tcurve = d.groupby("timestamp", as_index=False)["profit_and_loss"].sum().sort_values("timestamp")
        vals = tcurve["profit_and_loss"].to_numpy(float)
        if vals.size == 0:
            continue
        adjusted = vals + offset
        curve_parts.append(adjusted)
        offset = float(adjusted[-1])
        day_totals[int(day)] = float(offset - (adjusted[0] - vals[0]))

    if curve_parts:
        curve = np.concatenate(curve_parts)
        running_max = np.maximum.accumulate(curve)
        drawdown = running_max - curve
        max_dd = float(np.max(drawdown))
        curve_std = float(np.std(curve))
        step_std = float(np.std(np.diff(curve))) if curve.size > 1 else 0.0
        total_pnl = float(curve[-1])
    else:
        total_pnl = 0.0
        max_dd = 0.0
        curve_std = 0.0
        step_std = 0.0

    score = total_pnl - 0.35 * max_dd - 0.05 * step_std

    out = {
        "total_pnl": total_pnl,
        "max_drawdown": max_dd,
        "score": score,
        "curve_std": curve_std,
        "curve_step_std": step_std,
    }
    for day, pnl in day_totals.items():
        out[f"day_{day}_pnl"] = pnl
    return out


def load_manifest() -> dict[int, dict]:
    if not MANIFEST.exists():
        return {}
    data = json.loads(MANIFEST.read_text())
    return {int(x["trial"]): x for x in data}


def render_report(df: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Round 3 Trial Leaderboard",
        "",
        "## Overall Top 20",
        "",
    ]
    cols = ["trial", "set", "family", "score", "total_pnl", "max_drawdown", "curve_step_std", "status"]
    lines.append(df.sort_values("score", ascending=False).head(20)[cols].to_markdown(index=False, floatfmt=".2f"))
    lines.append("")

    for set_name in ["PACK_ONLY", "VELV_VEV_TARGET"]:
        lines.append(f"## Top 10 - {set_name}")
        lines.append("")
        sdf = df[df["set"] == set_name].sort_values("score", ascending=False).head(10)
        lines.append(sdf[cols].to_markdown(index=False, floatfmt=".2f"))
        lines.append("")

    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and rank Round 3 generated trials.")
    parser.add_argument("--start", type=int, default=1, help="First trial number.")
    parser.add_argument("--end", type=int, default=80, help="Last trial number (inclusive).")
    parser.add_argument("--days", type=str, default="0,1", help="Comma-separated days, e.g. 0,1")
    parser.add_argument("--timeout", type=int, default=120, help="Per-trial timeout seconds.")
    args = parser.parse_args()

    days = [int(x.strip()) for x in args.days.split(",") if x.strip()]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    rows = []
    for trial in range(args.start, args.end + 1):
        trial_dir = TRIALS_DIR / f"trial{trial}"
        trader_file = trial_dir / "trader.py"
        log_file = trial_dir / f"backtest_day_{'_'.join(map(str, days))}.log"
        meta_file = trial_dir / "metadata.json"

        if not trader_file.exists():
            rows.append({"trial": trial, "status": "missing_trader"})
            continue

        status = "ok"
        err_msg = ""
        ok, err_msg = run_backtest(trader_file, days, log_file, args.timeout)
        if not ok:
            status = "failed"

        metrics = parse_metrics(log_file) if ok and log_file.exists() else {
            "total_pnl": -1e12,
            "max_drawdown": 1e12,
            "score": -1e12,
            "curve_std": 1e12,
            "curve_step_std": 1e12,
        }

        meta = {}
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
        elif trial in manifest:
            meta = manifest[trial]

        row = {
            "trial": trial,
            "set": meta.get("set", "UNKNOWN"),
            "family": meta.get("family", "unknown"),
            "status": status,
            "error": err_msg,
            **metrics,
        }
        rows.append(row)
        print(f"trial{trial}: {status} score={row.get('score', float('nan')):.2f}")

    df = pd.DataFrame(rows).sort_values("trial")
    day_tag = "_".join(map(str, days))
    csv_path = RESULTS_DIR / f"leaderboard_day_{day_tag}.csv"
    md_path = RESULTS_DIR / f"leaderboard_day_{day_tag}.md"
    df.to_csv(csv_path, index=False)
    render_report(df, md_path)

    top_pack = df[df["set"] == "PACK_ONLY"].sort_values("score", ascending=False).head(10)
    top_vv = df[df["set"] == "VELV_VEV_TARGET"].sort_values("score", ascending=False).head(10)

    (RESULTS_DIR / f"top10_pack_day_{day_tag}.csv").write_text(top_pack.to_csv(index=False))
    (RESULTS_DIR / f"top10_velv_vev_day_{day_tag}.csv").write_text(top_vv.to_csv(index=False))

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
