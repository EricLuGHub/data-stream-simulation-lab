# Trial33 vs Trial5 Investigation (Submission Logs)

Compared files:
- R1/trial33/230137.json
- R1/trial5/123629.json

## Topline
- trial5 profit: 4884.9375
- trial33 profit: 4791.6875
- delta (trial33 - trial5): -93.25

## Per-product final PnL from activitiesLog
- trial5:
  - ASH_COATED_OSMIUM: 1164.9375
  - INTARIAN_PEPPER_ROOT: 3720.0
- trial33:
  - ASH_COATED_OSMIUM: 1702.96875
  - INTARIAN_PEPPER_ROOT: 3088.71875

PEPPER delta (trial33 - trial5): -631.28125
ASH delta (trial33 - trial5): +538.03125
Net: -93.25

## Position endpoint
- trial5 final positions:
  - ASH_COATED_OSMIUM: +18
  - INTARIAN_PEPPER_ROOT: +50
- trial33 final positions:
  - ASH_COATED_OSMIUM: -7
  - INTARIAN_PEPPER_ROOT: +23

Interpretation: on this submission day, trial5 carried materially more PEPPER inventory into the close (+50 vs +23).

## Where PEPPER gap opens
Bucket-end PEPPER PnL delta (trial33 - trial5):
- bucket 0: +12.0
- bucket 1: +17.492188
- bucket 2: -23.0
- bucket 3: -105.0
- bucket 4: -81.0
- bucket 5: -93.0
- bucket 6: -97.28125
- bucket 7: -214.1875
- bucket 8: -421.1875
- bucket 9: -631.28125

Interpretation: most underperformance accumulates late (buckets 7-9), consistent with lower late carry.

## Drawdown profile (graphLog)
- trial5 max drawdown: 65.59375
- trial33 max drawdown: 27.890625

Interpretation: trial33 appears to trade off some upside for a smoother path on this sample.

## Likely root cause
- Trial33 has stricter de-risking and lower net long carry versus trial5 on this specific run, which hurts when PEPPER drifts up into the close.
- Trial5 behaves more like high-carry hold-to-close in this environment.
