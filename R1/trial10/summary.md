# Trial 10: Wall-Mid + Regime Hybrid

Approach:
- Hybrid fair value: weighted blend of wall-mid and EMA(mid), with imbalance tilt.
- Regime-adaptive spread/size from spread + short realized volatility.
- Two-stage execution: take edge first, then make inventory-skewed quotes.
- Includes explicit inventory flattening beyond soft thresholds.

Why this hybrid:
- Combines the stable anchoring from wall-mid designs with adaptive quoting from regime-based market making.
