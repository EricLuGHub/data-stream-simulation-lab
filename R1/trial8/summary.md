# Trial 8: Short-Horizon Reversion Plus Defensive MM

Approach:
- Tracks a short rolling mean/std of mid-price and trades mean reversion only on meaningful z-score deviations.
- Uses fair anchored to rolling mean, with wider half-spread when deviation is large.
- Inventory gating is stricter (risk-increasing side can be shut off beyond +/-30).

Rationale:
- Tests whether ASH reverts over short windows while keeping a robust passive fallback.
