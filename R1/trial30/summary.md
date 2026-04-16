# Trial 30: Time-Profiled Trend Carry + Pullback Entries

## Hypothesis
Use a strong long-carry profile in early and mid buckets, then gradually reduce inventory while still buying residual dips in a persistent uptrend.

## Key design points
- PEPPER-only (`INTARIAN_PEPPER_ROOT`)
- Filtered wall-mid fair value (ignore tiny top-of-book noise)
- Drift + EMA blend for fair value anchor
- Time-bucket target path (0-9) with trend/z-score adjustments
- Sell suppression during positive-trend pullbacks

## Backtest (Round 1, all days)
- Day -2: 41,290
- Day -1: 38,324
- Day 0: 36,669
- Total: 116,283

Risk metrics:
- Sharpe: 16.5554
- Max drawdown abs: 636,539
- Calmar: 0.1827

## Notes
A strong improvement over Trial 5, but still below trial23-level totals.
