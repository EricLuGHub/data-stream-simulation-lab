# Round 1 Backtest Report (Trial 13 vs Trial 14, ASH-only)

## Scope
- Backtester: `../.venv/bin/prosperity4btest`
- Algorithms tested:
  - `R1/trial13/125304.py`
  - `R1/trial14/125405.py`
- Days run: `-2`, `-1`, `0`
- Command pattern:
  - `../.venv/bin/prosperity4btest <trial_file> 1-<day> --no-out`

These are ASH-only strategies, so PEPPER PnL is expected to be 0.

## Results by Trial and Day

| Trial | Day | ASH_COATED_OSMIUM | INTARIAN_PEPPER_ROOT | Total profit |
|---|---:|---:|---:|---:|
| 13 | -2 | 5,573 | 0 | 5,573 |
| 13 | -1 | 7,032 | 0 | 7,032 |
| 13 | 0 | 5,994 | 0 | 5,994 |
| 14 | -2 | 9,089 | 0 | 9,089 |
| 14 | -1 | 11,185 | 0 | 11,185 |
| 14 | 0 | 10,029 | 0 | 10,029 |

## Aggregate Summary

| Trial | ASH Sum | Total Sum | Average per Day |
|---|---:|---:|---:|
| 13 | 18,599 | 18,599 | 6,199.67 |
| 14 | 30,303 | 30,303 | 10,101.00 |

## Ranking
1. Trial 14: 30,303
2. Trial 13: 18,599

## Interpretation
- Trial 14, the more passive variant, clearly outperformed the aggressive variant on all three days.
- Trial 13 likely traded too often and paid more adverse selection, which is consistent with a strategy that pushes into edge too quickly on a fairly stable ASH tape.
- Trial 14 is the stronger candidate if you want a single ASH baseline right now.

## Practical Takeaway
- Keep the passive family as the base.
- Use aggressiveness only as a controlled overlay when spread or imbalance conditions are unusually favorable.
- If iterating further, tune the passive side first; aggressive crossing should stay selective.
