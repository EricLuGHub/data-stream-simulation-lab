# Trial 31: Regime-Persistence Pullback Engine

## Hypothesis
Your residual diagnostics showed most above/below-trend runs are short; buy persistent short pullbacks (2-6 ticks) and de-risk on persistent overextension.

## Key design points
- PEPPER-only (`INTARIAN_PEPPER_ROOT`)
- EMA + drift + microprice fair value
- Explicit residual-sign run-length state in `traderData`
- Entry biased to persistent pullbacks, not single-tick noise
- Fast de-risk when above-trend persistence and high z-score align

## Backtest (Round 1, all days)
- Day -2: 40,514
- Day -1: 38,936
- Day 0: 34,907
- Total: 114,357

Risk metrics:
- Sharpe: 13.1836
- Max drawdown abs: 589,300
- Calmar: 0.1941

## Notes
Safer profile than many aggressive variants, but weaker PnL than trial30/trial32.
