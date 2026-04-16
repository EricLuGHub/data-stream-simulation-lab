# Trial 24: PEPPER Vol-Spike Mean Reversion + Timeout

Inspiration from prior top teams:
- Volatility-triggered mean reversion entries.
- Time-in-position caps for risk control.

Design:
- PEPPER-only strategy.
- Enter contrarian positions only during high-volatility deviations from rolling mean.
- Enforce hard timeout exits on held positions.
- Add small carry layer to avoid total drift miss.

Backtest (Round 1):
- Day -2: 182
- Day -1: -671
- Day 0: -1,183
- Total: -1,672

Risk metrics:
- Sharpe: -0.8077
- Max drawdown abs: 227,824
- Calmar: -0.0073

Observations:
- This regime was not favorable for pure mean reversion.
- PEPPER's strong persistent drift made contrarian entries structurally weak.
- Timeout exits prevented larger losses but could not recover edge.
