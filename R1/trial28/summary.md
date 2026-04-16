# Trial 28 Summary

## Objective
Create a submission-hardened variant of trial26 with minimal PEPPER participation adjustments, while preserving the original signal structure.

## Code
- Base: trial26 merged ASH + PEPPER model
- File: 126402.py
- Changes are only in PEPPER:
  - Added no-fill tracking in traderData (`pepper_no_fill_steps`, `pepper_prev_pos`)
  - Slightly wider PEPPER taker threshold under persistent no-fill conditions
  - Small quote spread tightening when no-fill streak is high and trend is long
  - Small size boost under no-fill streak
  - Mildly relaxed sell suppression under no-fill streak

## Backtest (Round 1)
- Day -2: 53,190
- Day -1: 51,890
- Day 0: 50,191
- Total: 155,271

## Comparison
- Trial26 total: 156,267
- Trial28 total: 155,271
- Delta vs trial26: -996

## Conclusion
Trial28 is close but does not beat trial26 in local round-1 backtest. It is a safer participation variant worth keeping for submission testing, but trial26 remains the stronger local baseline.
