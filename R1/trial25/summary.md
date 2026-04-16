# Trial 25: PEPPER Phase-Switch Carry (Early Carry + Late Momentum)

Inspiration from prior top-team themes:
- Regime-specific behavior instead of one static policy.
- Distinct entry/exit posture across phases.

Design:
- PEPPER-only strategy.
- Early session: high long-carry target (similar to best carry profiles).
- Late session: tighter inventory and momentum-conditioned targets.
- Residual z-score used for pullback boosts and extension de-risking.

Backtest (Round 1):
- Day -2: 40,267
- Day -1: 38,669
- Day 0: 27,579
- Total: 106,515

Risk metrics:
- Sharpe: 5.1379
- Max drawdown abs: 589,300
- Calmar: 0.1807

Observations:
- Strong on days -2 and -1, but underperformed on day 0.
- The late-phase logic appears too aggressive in de-risking for one regime.
- Promising architecture, but still dominated by Trial 23.
