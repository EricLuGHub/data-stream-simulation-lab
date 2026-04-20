# R2 Trial 1 PEPPER Report

## Objective
Tune a PEPPER-only strategy for round 2 using the two in-notebook training days, then evaluate it on the held-out day 1 backtest.

## Setup
- Training days: round 2 day -1 and day 0
- Holdout day: round 2 day 1
- Market scope: `INTARIAN_PEPPER_ROOT` only
- Strategy style: higher-risk, longer-hold carry with more aggressive inventory retention than the earlier round-1 trial37 style

The final tuned strategy was saved as [r2_pepper_highrisk_tuned.py](r2_pepper_highrisk_tuned.py).

## Tuning outcome
I ran a small focused parameter sweep on the two training days and selected the best candidate by total training profit.

Best training result:
- Round 2 day -1 and day 0 combined profit: `99,135`
- Best parameter set: `(0.0, 4.0, 3.0, 4.0, 3.0, 34, 42, 28, 12)`

## Holdout backtest
The tuned strategy was then backtested on round 2 day 1.

Holdout result:
- Round 2 day 1 profit: `49,121`

The backtest log is saved at [day1_backtest.log](day1_backtest.log).

## Interpretation
This is a positive holdout outcome. The strategy did not collapse out of sample, and it still produced meaningful profit on the unseen day 1.

What the result suggests:
- The carry/inventory-retention bias is still usable on the new data.
- The strategy is aggressive enough to make money on the holdout without needing ASH at all.
- Performance is lower on the holdout than on the training split, which is expected, but it remains solidly profitable.

## Important caveats
- The strategy is PEPPER-only, so this result does not say anything about ASH.
- The backtest reported very large drawdown percentages, so the raw PnL is good, but the risk profile needs caution.
- The tuning sweep was intentionally small and focused. It is good enough to identify a stronger variant, but it is not exhaustive.

## Bottom line
The tuned PEPPER trial worked on the held-out day 1 and stayed profitable. I would treat it as a usable candidate, but with a clear warning that it is high-risk and should be compared against a more conservative variant before final selection.
