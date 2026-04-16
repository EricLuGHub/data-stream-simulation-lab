# Trial 22: PEPPER Long-Carry Hybrid (Momentum + Pullback Adaptation)

Objective:
- Build a PEPPER-only model that keeps Trial 5's strong long-carry behavior while improving weaker late-session performance.

Design choices:
- Core fair value: anchored linear trend + EMA blend.
- Directional context: fast-vs-slow EMA slope signal.
- Residual context: rolling residual z-score for pullback/extension adaptation.
- Inventory control:
  - High base long target early in day, then gradual decay.
  - Target boosts during positive momentum and negative residual pullbacks.
  - Target reduction only on strong extension.
- Execution:
  - Aggressive taker buys on pullback/momentum continuation.
  - Taker sells only when clearly extended or over-target.
  - Passive sell suppression while under long target.

Round 1 results (PEPPER only):
- Day -2: 34,774
- Day -1: 35,410
- Day 0: 36,031
- Total: 106,216

Comparison against prior PEPPER baselines:
- Trial 5 PEPPER total: 103,129
- Trial 20 PEPPER total: 88,128.5
- Trial 21 PEPPER total: 86,609.5
- Trial 19 PEPPER total: 78,671

Improvement vs Trial 5 (PEPPER):
- Absolute gain: +3,087
- Day-by-day edge: +1,441 (day -2), +600 (day -1), +1,045 (day 0)

Risk metrics from backtester:
- Sharpe: 56.3540
- Max drawdown (abs): 646,767
- Calmar: 0.1642

Notes:
- This trial outperforms Trial 5 on PEPPER PnL while remaining PEPPER-only.
- Trial 5 still has additional ASH PnL in full-strategy comparisons; this result is strictly for PEPPER model quality.
