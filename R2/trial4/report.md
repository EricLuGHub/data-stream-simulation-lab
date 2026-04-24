# R2 Trial 4 ASH Report

## Objective
Start from trial14, apply mild tuning on R2 days -1 and 0, and test on the held-out R2 day 1 to limit overfitting.

## Setup
- Base strategy: trial14 ASH
- Training days: round 2 day -1 and day 0
- Holdout day: round 2 day 1
- Product: ASH_COATED_OSMIUM only
- Tuning style: conservative to moderate changes only

Final strategy file: [r2_ash_trial14_tuned.py](r2_ash_trial14_tuned.py)

## Results
- Best train PnL (days -1 and 0): **21,777**
- Holdout day 1 PnL: **10,777**
- Full round 2 PnL: **32,554**

### Day-by-day PnL
| Day | ASH PnL |
|---:|---:|
| -1 | 10,714 |
| 0 | 11,063 |
| 1 | 10,777 |

### Risk Metrics (Full Round 2)
- Sharpe ratio: 58.3419
- Annualized Sharpe: 926.1491
- Sortino ratio: inf
- Max drawdown abs: 726,846
- Max drawdown pct: 282.4839
- Calmar ratio: 0.0448
