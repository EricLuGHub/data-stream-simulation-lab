# Trial 21: PEPPER Hybrid Trend-Anchor + Residual Z-Gating

Strategy intent:
- Trade only `INTARIAN_PEPPER_ROOT` and ignore ASH.
- Blend trend-following context with residual pullback entries.
- Prioritize buying pullbacks and avoid extension chasing unless extension is very strong.

Implementation details:
- Fair model:
  - Anchored trend slope `0.001` from first timestamp.
  - EMA blend `fair = 0.55 * trend + 0.45 * ema`.
- Residual control:
  - Rolling 120-point residual history with sigma floor `0.9`.
  - Aggressive buy when `z <= -1.4`.
  - Small profit-taking only when `z >= 2.6`.
- Dynamic inventory target by z bucket (`10` to `42`) with inventory-skewed passive quotes.

Round 1 backtest results:
- Day -2: `29,796`
- Day -1: `28,982`
- Day 0: `27,831`
- Total: `86,610`

Risk metrics (from backtester):
- Sharpe: `29.2341`
- Max drawdown (abs): `760,315`
- Calmar: `0.1139`

Observations:
- Second-best total PnL among trials 19-21 and very stable day-to-day returns.
- Better drawdown profile than Trial 19, but weaker than Trial 20.
- Hybrid logic appears robust, but likely leaves some upside versus pure continuation in strong trend segments.

Next tuning ideas:
- Add mild momentum overlay so target inventory increases when fast-minus-slow trend stays positive.
- Tighten sell trigger for `z >= 2.6` to avoid giving back gains on fast reversions.
