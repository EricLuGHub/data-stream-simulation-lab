# Round 3 Experiment Pipeline

This folder implements the Phase C to Phase H workflow for Round 3 strategy search.

## What This Creates

- 80 initial trials
  - `trial1` to `trial40`: `PACK_ONLY`
  - `trial41` to `trial80`: `VELV_VEV_TARGET`
- Batch backtest + ranking artifacts
- Top-10 per set extracts
- 10 refined trials
  - `trial81` to `trial90`

All trials are generated under `R3/trials/trialN`.

## 1) Generate 80 Initial Trials

```bash
python R3/experiments/generate_round3_trials.py
```

Outputs:
- `R3/experiments/trial_manifest.json`
- `R3/trials/trial1` ... `R3/trials/trial80`

## 2) Backtest And Rank Initial 80 (Days 0 and 1)

```bash
python R3/experiments/run_round3_trials.py --start 1 --end 80 --days 0,1
```

Outputs (in `R3/experiments/results`):
- `leaderboard_day_0_1.csv`
- `leaderboard_day_0_1.md`
- `top10_pack_day_0_1.csv`
- `top10_velv_vev_day_0_1.csv`

## 3) Generate 10 Refined Trials From Top Strategies

```bash
python R3/experiments/promote_top_trials.py --leaderboard leaderboard_day_0_1.csv --start 81
```

Outputs:
- `R3/experiments/refined_manifest.json`
- `R3/trials/trial81` ... `R3/trials/trial90`

## 4) Backtest Refined Trials (Days 0 and 1)

```bash
python R3/experiments/run_round3_trials.py --start 81 --end 90 --days 0,1
```

## 5) Holdout Check (Day 2 only)

```bash
python R3/experiments/run_round3_trials.py --start 81 --end 90 --days 2
```

## Notes

- This setup follows your anti-overfit policy: tune/select with day 0 and day 1, then validate on day 2.
- `score` is `total_pnl - 0.35 * max_drawdown - 0.05 * curve_step_std`.
- You can change trial generation logic in `generate_round3_trials.py` without touching runner/report code.
