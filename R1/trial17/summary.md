# Trial 17: Tuned Regime-Hysteresis Hybrid

Approach:
- Built as a tuned version of Trial 16 with the same trend/reversion split, but with mode hysteresis to reduce flip-flopping.
- Trend mode is slightly more decisive (faster fair, tighter spread, dynamic take width) to preserve upside.
- Reversion mode remains inventory-aware and less aggressive to avoid unnecessary churn.

Tuning goals:
- Keep Trial 16's upside profile stronger than the ultra-conservative Trial 15 style.
- Reduce noise from rapid mode changes and improve risk-adjusted behavior via earlier inventory brakes.
