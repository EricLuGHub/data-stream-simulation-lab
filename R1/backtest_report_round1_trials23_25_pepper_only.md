# Round 1 PEPPER-Only Report: New Wild-Idea Trials (23-25)

Research-inspired motifs used:
- Filtered order-book fair value (ignore tiny noisy levels).
- Regime/side gating from short-vs-long trend windows.
- Dynamic inventory targets rather than fixed static quoting.
- Keep models structurally simple with interpretable levers.

## Results

| Trial | Day -2 | Day -1 | Day 0 | Total PEPPER PnL | Sharpe | Max Drawdown Abs | Calmar |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| trial23 | 44504 | 40874 | 40586 | 125964 | 19.2282 | 633100 | 0.1990 |
| trial25 | 40267 | 38669 | 27579 | 106515 | 5.1379 | 589300 | 0.1807 |
| trial24 | 182 | -671 | -1183 | -1672 | -0.8077 | 227824 | -0.0073 |

## Baseline context

| Baseline | Total PEPPER PnL |
| --- | ---: |
| trial5 | 103129 |
| trial22 | 106216 |

## Key conclusions

1. trial23 is the standout and clearly beats all current PEPPER baselines, including trial5 and trial22.
2. trial25 is positive and competitive with trial22, but not robust enough across all days.
3. trial24 confirms that this PEPPER regime punishes heavy mean-reversion bias.

## Recommendation

- Promote trial23 as the new PEPPER candidate baseline.
- Use trial25 as a backup template for further late-phase tuning.
- Retire or heavily rework trial24.
