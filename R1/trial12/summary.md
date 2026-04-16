# Trial 12: Ensemble Fair-Value Hybrid

Approach:
- Ensemble fair value from wall-mid, EMA(mid), and short/long rolling means.
- Includes order-book imbalance correction.
- Uses spread/z-sensitive taking and inventory-skewed passive making.
- Adds defensive mode when inventory and z-score indicate same-direction risk.

Why this hybrid:
- Explicitly combines independent fair proxies to reduce sensitivity to a single noisy signal.
