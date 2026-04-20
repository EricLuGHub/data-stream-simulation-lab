# Trial 35: Trial33 Ablation A (Lower Late Carry)

## Objective
Isolate whether trial33 gains are driven by higher late-session target inventory.

## Single change vs trial33
- Changed only `target_by_bucket` for late buckets:
  - from `[... 33, 31, 30, 30]`
  - to   `[... 33, 28, 24, 24]`
- All other logic unchanged.

## Backtest (Round 1)
- Day -2: 44,025
- Day -1: 42,304
- Day 0: 39,110
- Total: 125,439

## Delta vs trial33
- Trial33 total: 130,558
- Trial35 total: 125,439
- Delta: -5,119

## Conclusion
Reducing late-session carry removes most of trial33's gain. Late-bucket inventory retention is a primary performance driver.
