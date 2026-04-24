# R2 Trial 5 Report: Trial4 ASH + Trial2 PEPPER

## Objective
Create a merged strategy that combines:
- ASH logic from trial4 (`r2_ash_trial14_tuned.py`), and
- PEPPER logic from trial2 (`r2_pepper_maf_aware.py`).

## Implementation Notes
The merged file is `r2_trial5_merge_ash_trial4_pepper_trial2.py`.

Key implementation details:
- Both products are traded in a single `Trader` class.
- Trader state is namespaced to prevent collisions:
  - `traderData["ash"]` for ASH state
  - `traderData["pepper"]` for PEPPER state
- Position limits remain 50 per product, matching source strategies.
- ASH and PEPPER logic blocks are preserved from their source trials.

## Backtest Setup
- Command: `./.venv/bin/prosperity4btest R2/trial5/r2_trial5_merge_ash_trial4_pepper_trial2.py 2 --data R2 --merge-pnl --no-progress --out R2/trial5/full_round2_backtest.log`
- Dataset: round 2 full set (days -1, 0, 1)

## Results
### Total PnL by Day
| Day | Total PnL |
|---:|---:|
| -1 | 59,990 |
| 0 | 60,698 |
| 1 | 60,546 |

Full round-2 total: **181,234**

### Product-Level PnL
| Day | ASH | PEPPER | Total |
|---:|---:|---:|---:|
| -1 | 10,714 | 49,276 | 59,990 |
| 0 | 11,063 | 49,635 | 60,698 |
| 1 | 10,777 | 49,768 | 60,546 |

### Risk Metrics (full stitched run)
- Sharpe ratio: 162.1228
- Annualized Sharpe: 2,573.6200
- Sortino ratio: inf
- Max drawdown abs: 991,379
- Max drawdown pct: 353.7690
- Calmar ratio: 0.1828

## Interpretation
The merged trial keeps the high PEPPER contribution from trial2 and adds the stronger trial4 ASH leg on top. On this local backtest, the combination produces a higher total than either single-product leg alone.

## Output Files
- Strategy: `r2_trial5_merge_ash_trial4_pepper_trial2.py`
- Backtest log: `full_round2_backtest.log`
