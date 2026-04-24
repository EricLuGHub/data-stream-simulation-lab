# R2 Trial 3 ASH Report

## Objective
Tune a higher-risk ASH-only strategy on round 2 days -1 and 0, then report the full round 2 PnL across all days.

## Setup
- Training days: round 2 day -1 and day 0
- Holdout day: round 2 day 1
- Market scope: `ASH_COATED_OSMIUM` only
- Style: higher-risk carry with faster inventory rotation than the passive round-1 baseline

The final tuned strategy was saved at [r2_ash_highrisk_tuned.py](r2_ash_highrisk_tuned.py).

## Tuning outcome
Best training result on days -1 and 0: **14,798**

## Holdout and full backtest
Holdout day 1 profit: **6,699**

Full round 2 profit: **21,497**

## Daily PnL
| Day | ASH PnL |
|---:|---:|
| -1 | 7,192 |
| 0 | 7,606 |
| 1 | 6,699 |

Total round 2 PnL: **21,497**

Risk metrics from the full round-2 backtest:
- Sharpe ratio: 15.7809
- Annualized Sharpe: 250.5135
- Sortino ratio: inf
- Max drawdown abs: 504,775
- Max drawdown pct: 416.9317
- Calmar ratio: 0.0426

## Interpretation
The strategy stayed profitable on every round-2 day, but the drawdown profile is still aggressive. Compared with the passive round-1 ASH baseline, this version is clearly more active and better suited to a higher-risk submission style.
