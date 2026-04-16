# Trial 19: PEPPER Pullback-to-Trend Re-entry

Strategy intent:
- Trade only `INTARIAN_PEPPER_ROOT` and ignore ASH.
- Use anchored linear trend + EMA blend as fair value.
- Buy aggressively on negative residual shocks (`z <= -1.8`) to capture pullback reversion toward trend.
- Keep a long bias by suppressing routine selling; only lighten inventory on extreme positive extension (`z >= 2.8`) or stretched long inventory.

Implementation details:
- Fair model: `fair = 0.65 * trend + 0.35 * ema`.
- Trend slope: `0.001` per timestamp from first observed anchor.
- Residual scaling: rolling 80-point residual standard deviation with floor `0.8`.
- Positioning:
  - Dynamic target inventory from z-regime (`12` to `40`, default `28`).
  - Passive quoting around fair with inventory skew.

Round 1 backtest results:
- Day -2: `31,595`
- Day -1: `23,300`
- Day 0: `23,776`
- Total: `78,671`

Risk metrics (from backtester):
- Sharpe: `5.6301`
- Max drawdown (abs): `1,026,465`
- Calmar: `0.0766`

Observations:
- The pullback entry logic monetizes PEPPER's residual mean reversion well and never trades ASH.
- Performance is profitable on all 3 available days, but variance is higher than the other two new trials.
- Drawdown is the largest among trials 19-21, suggesting this version is too aggressive in re-entry sizing during adverse paths.

Next tuning ideas:
- Reduce taker cap on shock entries (`10 -> 6 or 7`) to lower drawdown.
- Add time-based decay on target inventory late in day to avoid carrying oversized exposure into weaker windows.
