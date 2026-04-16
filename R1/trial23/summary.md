# Trial 23: PEPPER Wall-Mid Trend Gating

Inspiration from prior top teams:
- Use filtered order-book fair value (ignore tiny noisy levels).
- Regime-aware side gating (in uptrend, suppress one side to stay with flow).
- Keep strategy structurally simple and robust rather than over-parameterized.

Design:
- PEPPER-only strategy.
- Fair value blend:
  - filtered wall-mid (volume-filtered top levels),
  - short-horizon mean,
  - anchored linear drift component.
- Regime signal from short-vs-long moving averages.
- Dynamic target inventory with pullback/extension z-score adjustments.
- Aggressive buy taking around fair; controlled sells only on stronger extension.

Backtest (Round 1):
- Day -2: 44,504
- Day -1: 40,874
- Day 0: 40,586
- Total: 125,964

Risk metrics:
- Sharpe: 19.2282
- Max drawdown abs: 633,100
- Calmar: 0.1990

Observations:
- Outperforms Trial 5 PEPPER and all recent PEPPER variants by a wide margin.
- Most edge comes from sustained long carry plus improved fair-value filtering.
- Less late-session decay than Trial 5 because side gating adapts with trend state.
