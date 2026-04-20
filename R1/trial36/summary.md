# Trial 36: Trial33 Ablation B (Earlier De-risk Trigger)

## Objective
Isolate impact of the stricter de-risk trigger in trial33.

## Single change vs trial33
- Changed only de-risk trigger thresholds:
  - from `z >= 2.9` and `slope < -0.5`
  - to   `z >= 2.7` and `slope < -0.4`
- All other logic unchanged.

## Backtest (Round 1)
- Day -2: 45,310
- Day -1: 44,235
- Day 0: 41,013
- Total: 130,558

## Delta vs trial33
- Trial33 total: 130,558
- Trial36 total: 130,558
- Delta: 0

## Conclusion
This trigger change was effectively inactive on this sample path. The performance lift in trial33 is not explained by this lever.

PNL: ..