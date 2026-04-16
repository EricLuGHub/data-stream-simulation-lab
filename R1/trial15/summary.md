# Trial 15: Conservative Inventory-First Liquidity Provider

Approach:
- Anchors fair value to a stable blend of wall-mid, slow EMA, and short rolling mean.
- Minimizes active taking; only unwinds inventory when position pressure is high.
- Quotes wider and smaller in noisy states, and applies strong inventory skew.

Motivation from logs:
- Trial 14 outperformed aggressive variants, suggesting safer spread capture and stricter inventory control were beneficial.
- Trials 10-13 had large PnL swings; this design intentionally trades less and emphasizes drawdown control.
