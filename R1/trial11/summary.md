# Trial 11: Signal-Blend + Z-Score Gate Hybrid

Approach:
- Blends wall-mid anchor with EMA plus imbalance fair estimate.
- Uses rolling z-score as a confidence gate for taking aggressiveness.
- Makes around fair with inventory skew and state-aware quote sizing.
- Adds stronger unwind pressure in stretched z-score states and high inventory states.

Why this hybrid:
- Combines microstructure fair-value signals with short-horizon reversion state detection without hard-coding a fixed anchor.
