# Trial 29 Summary

## Objective
Test a quote-only PEPPER participation tweak relative to trial26.

## Code
- Base: trial26 merged ASH + PEPPER model
- File: 126403.py
- Changes limited to PEPPER maker side:
  - No-fill streak tracking (`pepper_prev_pos`, `pepper_no_fill_steps`)
  - Conditional 1-tick quote tightening under sparse fills
  - Small maker size lift under sparse fills
- PEPPER taker signal and target logic left unchanged.

## Backtest (Round 1)
- Day -2: 51,845
- Day -1: 51,231
- Day 0: 47,855
- Total: 150,931

## Comparison
- Trial26 total: 156,267
- Trial29 total: 150,931
- Delta vs trial26: -5,336

## Conclusion
Quote-only participation tuning reduced PnL versus trial26 in local round-1 tests. Trial26 remains the best local baseline among the recent merged variants.
