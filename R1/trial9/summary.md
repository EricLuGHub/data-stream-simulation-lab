# Trial 9: Regime-Adaptive Market Maker

Approach:
- Detects simple micro-regimes from current spread and short realized volatility.
- Tight regime: narrower quotes and lighter taking.
- Wide/volatile regime: wider quotes, larger make size, stricter take threshold.
- Fair value remains EMA plus imbalance with inventory-skewed quoting.

Rationale:
- Tests whether adaptive quote width/size helps ASH execution quality across changing market states.
