# Trial 16: Regime-Switching Trend/Reversion Hybrid

Approach:
- Uses a mode switch: trend-following when short-vs-long mean divergence is strong, reversion mode otherwise.
- Trend mode: tighter fair around fast EMA + imbalance, moderate taker activity, directional quote sizing.
- Reversion mode: wider quotes, lower take cap, stronger inventory-first behavior.

Motivation from logs:
- Existing hybrids remained profitable but had noisy PnL paths; this design tries to reduce unnecessary aggression while still exploiting directional phases.
- It deliberately differs from Trial 15 by using explicit regime switching instead of purely conservative spread capture.
