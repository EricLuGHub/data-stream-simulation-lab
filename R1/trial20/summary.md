# Trial 20: PEPPER Momentum Continuation with Trailing Exits

Strategy intent:
- Trade only `INTARIAN_PEPPER_ROOT` and ignore ASH.
- Follow directional continuation when fast trend is above slow trend.
- Keep long inventory in up-regime, then de-risk quickly when momentum weakens.

Implementation details:
- Regime signal:
  - `ema_fast = 0.40 * mid + 0.60 * prev_fast`
  - `ema_slow = 0.08 * mid + 0.92 * prev_slow`
  - Up regime when `ema_fast - ema_slow > 1.2`.
  - Down/weak regime when signal falls below `0.2` or `< -0.8`.
- Fair model: `fair = 0.75 * ema_fast + 0.25 * ema_slow`.
- Entry/exit behavior:
  - Breakout-style buys in up regime via taker logic.
  - Trailing de-risk sells when momentum weakens.
  - Inventory target shifts by regime (`34` up, `14` neutral, `2` down).

Round 1 backtest results:
- Day -2: `27,340`
- Day -1: `29,989`
- Day 0: `30,800`
- Total: `88,128`

Risk metrics (from backtester):
- Sharpe: `16.2316`
- Max drawdown (abs): `542,156`
- Calmar: `0.1626`

Observations:
- Best total PnL across the three new PEPPER-only trials.
- PnL is balanced and strong across all three days; no weak day outlier.
- Drawdown is materially lower than Trial 19 and lower than Trial 21, while keeping the highest profit.

Next tuning ideas:
- Add residual-based filter to avoid overpaying on local positive extension during breakout entries.
- Reduce sell suppression in late-day windows to lock in gains when trend flattening appears.
