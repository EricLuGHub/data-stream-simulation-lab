# Trial 32: Participation-Adaptive Carry + Bucket Awareness

## Hypothesis
When fills slow down, increase controlled aggression while preserving trend-carry logic; use intraday bucket profile from log analysis.

## Key design points
- PEPPER-only (`INTARIAN_PEPPER_ROOT`)
- No-fill streak tracking (`no_fill`, `prev_pos`) in `traderData`
- Filtered wall-mid plus drift/EMA fair value
- Bucket-dependent target inventory
- Participation-aware quote tightening and taker edge

## Backtest (Round 1, all days)
- Day -2: 43,926
- Day -1: 42,285
- Day 0: 38,992
- Total: 125,203

Risk metrics:
- Sharpe: 16.6096
- Max drawdown abs: 634,900
- Calmar: 0.1972

## Notes
Very close to trial23, and stronger than most historical PEPPER-only variants.
