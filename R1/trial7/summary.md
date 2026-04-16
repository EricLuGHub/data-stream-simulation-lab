# Trial 7: EMA Plus Imbalance Market Making

Approach:
- Fair value = EMA(mid) + order-book imbalance adjustment.
- Takes clear edge only when quotes are beyond a small band from fair.
- Passive quotes are inventory-skewed and one-tick improved when still edge-positive.
- Adds soft inventory guardrails near extreme positions.

Rationale:
- Uses ASH microstructure signals from your notebooks while staying in a conservative market-making framework.
