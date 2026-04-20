# Trial 37: Submission-Focused Trial33 Variant (Higher Late Carry)

## Objective
Increase late-session PEPPER inventory carry to better match submission-day behavior where hold-to-close long exposure outperformed.

## Single change vs trial33
- Only changed `target_by_bucket` late profile:
  - trial33: `[... 33, 31, 30, 30]`
  - trial37: `[... 33, 44, 46, 48]`
- All other logic unchanged.

## Backtest (Round 1)
- Day -2: 48,602
- Day -1: 48,691
- Day 0: 48,164
- Total: 145,457

## Comparison
- Trial33 total: 130,558
- Trial37 total: 145,457
- Delta vs trial33: +14,899

- Trial5 total (PEPPER-only baseline context): 103,129
- Delta vs trial5: +42,328

## Notes
This variant materially improves local round-1 PEPPER PnL and is consistent with the submission-log diagnosis that trial33 was under-carrying late.


PNL sub: 3.3k