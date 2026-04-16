# Round 1 Backtest Report (Hybrid ASH-only trials 10 to 12)

## Scope
- Backtester: `../.venv/bin/prosperity4btest`
- Algorithms tested:
  - `R1/trial10/125001.py`
  - `R1/trial11/125102.py`
  - `R1/trial12/125203.py`
- Days run: `-2`, `-1`, `0`
- Command pattern:
  - `../.venv/bin/prosperity4btest <trial_file> 1-<day> --no-out`

These are ASH-only strategies, so PEPPER PnL is expected to be 0.

## Results by Trial and Day

| Trial | Day | ASH_COATED_OSMIUM | INTARIAN_PEPPER_ROOT | Total profit |
|---|---:|---:|---:|---:|
| 10 | -2 | 8,164 | 0 | 8,164 |
| 10 | -1 | 9,494 | 0 | 9,494 |
| 10 | 0 | 8,560 | 0 | 8,560 |
| 11 | -2 | 6,365 | 0 | 6,365 |
| 11 | -1 | 7,438 | 0 | 7,438 |
| 11 | 0 | 6,978 | 0 | 6,978 |
| 12 | -2 | 8,372 | 0 | 8,372 |
| 12 | -1 | 9,893 | 0 | 9,893 |
| 12 | 0 | 8,615 | 0 | 8,615 |

## Aggregate Summary

| Trial | ASH Sum | Total Sum | Average per Day |
|---|---:|---:|---:|
| 10 | 26,218 | 26,218 | 8,739.33 |
| 11 | 20,781 | 20,781 | 6,927.00 |
| 12 | 26,880 | 26,880 | 8,960.00 |

## Ranking
1. Trial 12: 26,880
2. Trial 10: 26,218
3. Trial 11: 20,781

## Interpretation
- Trial 12 performed best and was most consistent across all three days.
- Trial 10 was close behind, suggesting wall-mid plus regime adaptation is robust.
- Trial 11 underperformed the other hybrids, likely due to a stricter z-score gating profile reducing opportunistic fills.

## Recommended Next Step
- Promote Trial 12 as the current ASH baseline.
- Keep Trial 10 as a backup baseline.
- If doing a follow-up iteration, do small sensitivity checks around inventory thresholds and wall-volume cutoffs only (avoid broad parameter sweeps).
