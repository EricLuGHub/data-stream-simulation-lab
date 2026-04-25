from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from generate_round3_trials import PACK_TEMPLATE, VOUCHER_TEMPLATE, write_trial


ROOT = Path(__file__).resolve().parents[2]
TRIALS_DIR = ROOT / "R3" / "trials"
RESULTS_DIR = ROOT / "R3" / "experiments" / "results"


def load_meta(trial: int) -> dict[str, Any]:
    meta_path = TRIALS_DIR / f"trial{trial}" / "metadata.json"
    return json.loads(meta_path.read_text())


def mutate_pack(params: dict[str, Any], i: int) -> dict[str, Any]:
    out = dict(params)
    if i % 2 == 0:
        out["take_edge"] = round(max(0.5, float(out["take_edge"]) * 0.9), 4)
        out["make_edge"] = round(max(1.0, float(out["make_edge"]) - 0.2), 4)
    else:
        out["take_edge"] = round(min(2.0, float(out["take_edge"]) * 1.1), 4)
        out["make_edge"] = round(min(2.6, float(out["make_edge"]) + 0.2), 4)

    out["signal_weight"] = round(max(0.4, float(out["signal_weight"]) * (1.05 if i < 3 else 0.95)), 4)
    out["inventory_skew"] = round(max(0.5, min(2.8, float(out["inventory_skew"]) * (0.9 if i in (1, 3) else 1.1))), 4)
    out["quote_size"] = int(max(10, min(24, int(out["quote_size"]) + (2 if i % 2 == 0 else -2))))
    out["max_take"] = int(max(8, min(22, int(out["max_take"]) + (2 if i in (0, 4) else -1))))
    return out


def mutate_velv_vev(params: dict[str, Any], i: int) -> dict[str, Any]:
    out = dict(params)
    out["tau_scale"] = round(max(180.0, min(380.0, float(out["tau_scale"]) + (-20.0 if i % 2 == 0 else 20.0))), 4)
    out["sigma_scale"] = round(max(0.75, min(1.2, float(out["sigma_scale"]) * (1.03 if i < 3 else 0.97))), 4)
    out["edge_mult"] = round(max(0.65, min(1.35, float(out["edge_mult"]) * (0.95 if i in (0, 2, 4) else 1.05))), 4)
    out["join_size"] = int(max(8, min(24, int(out["join_size"]) + (2 if i % 2 == 0 else -2))))
    out["max_take_mid"] = int(max(10, min(24, int(out["max_take_mid"]) + (2 if i < 2 else -1))))
    out["max_take_wing"] = int(max(6, min(16, int(out["max_take_wing"]) + (1 if i in (1, 3) else -1))))
    out["velv_take_edge"] = round(max(0.8, min(2.1, float(out["velv_take_edge"]) + (0.1 if i % 2 else -0.1))), 4)
    out["velv_make_edge"] = round(max(1.1, min(2.6, float(out["velv_make_edge"]) + (-0.1 if i % 2 else 0.1))), 4)
    out["velv_signal_weight"] = round(max(0.8, min(2.2, float(out["velv_signal_weight"]) * (1.05 if i in (0, 3) else 0.95))), 4)
    return out


def render_pack(params: dict[str, Any]) -> str:
    return PACK_TEMPLATE.format(**params)


def render_velv_vev(params: dict[str, Any]) -> str:
    fmt = dict(params)
    fmt["velv_enable"] = "True" if bool(fmt["velv_enable"]) else "False"
    fmt["traded_list"] = repr(fmt["traded_list"])
    return VOUCHER_TEMPLATE.format(**fmt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create improved 10 trials from top-10 per set.")
    parser.add_argument("--leaderboard", type=str, default="leaderboard_day_0_1.csv")
    parser.add_argument("--start", type=int, default=81)
    args = parser.parse_args()

    lb_path = RESULTS_DIR / args.leaderboard
    if not lb_path.exists():
        raise FileNotFoundError(f"Leaderboard not found: {lb_path}")

    lb = pd.read_csv(lb_path)
    lb = lb[lb["status"] == "ok"]

    pack_top = lb[lb["set"] == "PACK_ONLY"].sort_values("score", ascending=False).head(5)
    vv_top = lb[lb["set"] == "VELV_VEV_TARGET"].sort_values("score", ascending=False).head(5)

    next_trial = args.start
    new_manifest = []

    for i, row in enumerate(pack_top.itertuples(index=False)):
        meta = load_meta(int(row.trial))
        params = mutate_pack(meta["params"], i)
        code = render_pack(params)
        out_meta = {
            "trial": next_trial,
            "set": "PACK_ONLY",
            "family": "pack_refined",
            "parent_trial": int(row.trial),
            "params": params,
        }
        write_trial(next_trial, code, out_meta)
        new_manifest.append(out_meta)
        next_trial += 1

    for i, row in enumerate(vv_top.itertuples(index=False)):
        meta = load_meta(int(row.trial))
        params = mutate_velv_vev(meta["params"], i)
        code = render_velv_vev(params)
        out_meta = {
            "trial": next_trial,
            "set": "VELV_VEV_TARGET",
            "family": "velv_vev_refined",
            "parent_trial": int(row.trial),
            "params": params,
        }
        write_trial(next_trial, code, out_meta)
        new_manifest.append(out_meta)
        next_trial += 1

    manifest_path = ROOT / "R3" / "experiments" / "refined_manifest.json"
    manifest_path.write_text(json.dumps(new_manifest, indent=2, sort_keys=True))

    print(f"Created {len(new_manifest)} refined trials from {lb_path.name}")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
