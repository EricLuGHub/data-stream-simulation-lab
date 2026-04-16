# Round 1 Backtest Report (ASH-only trials 6 to 9)

## Scope
- Backtester: `../.venv/bin/prosperity4btest`
- Algorithms tested:
  - `R1/trial6/124601.py`
  - `R1/trial7/124702.py`
  - `R1/trial8/124803.py`
  - `R1/trial9/124904.py`
- Days run for Round 1: `-2`, `-1`, `0`
- Command pattern:
  - `../.venv/bin/prosperity4btest <trial_file> 1-<day> --no-out`

These are ASH-only traders by design, so PEPPER contribution is expected to be 0.

## Results by Trial and Day

| Trial | Day | ASH_COATED_OSMIUM | INTARIAN_PEPPER_ROOT | Total profit |
|---|---:|---:|---:|---:|
| 6 | -2 | 6,370 | 0 | 6,370 |
| 6 | -1 | 7,844 | 0 | 7,844 |
| 6 | 0 | 7,132 | 0 | 7,132 |
| 7 | -2 | 4,720 | 0 | 4,720 |
| 7 | -1 | 5,955 | 0 | 5,955 |
| 7 | 0 | 5,251 | 0 | 5,251 |
| 8 | -2 | 6,897 | 0 | 6,897 |
| 8 | -1 | 8,778 | 0 | 8,778 |
| 8 | 0 | 7,666 | 0 | 7,666 |
| 9 | -2 | 8,036 | 0 | 8,036 |
| 9 | -1 | 9,293 | 0 | 9,293 |
| 9 | 0 | 8,250 | 0 | 8,250 |

## Aggregate Summary by Trial (Across 3 Days)

| Trial | ASH Sum | Total Sum | Average per Day |
|---|---:|---:|---:|
| 6 | 21,346 | 21,346 | 7,115.33 |
| 7 | 15,926 | 15,926 | 5,308.67 |
| 8 | 23,341 | 23,341 | 7,780.33 |
| 9 | 25,579 | 25,579 | 8,526.33 |

## Ranking
1. Trial 9 (regime-adaptive market making): 25,579
2. Trial 8 (short-horizon reversion + defensive MM): 23,341
3. Trial 6 (wall-mid take-then-make): 21,346
4. Trial 7 (EMA + imbalance MM): 15,926

## Notes on Robustness
- Trials were built as distinct strategy families (wall-mid, EMA/imbalance, z-score reversion, regime-adaptive) instead of parameter over-tuning one baseline.
- A single backtest pass across all available Round 1 days was used for evaluation.
- Next iteration should still prioritize out-of-sample checks and sensitivity sweeps over narrow parameter fitting.
