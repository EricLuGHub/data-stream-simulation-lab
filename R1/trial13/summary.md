# Trial 13: Aggressive Hybrid

Approach:
- Faster EMA reaction and tighter take thresholds than the prior hybrids.
- More willing to cross or take when edge appears.
- Stronger directional lean when z-score and imbalance point the same way.
- Still keeps inventory guardrails, but they are less restrictive than the passive variant.

Why this one is aggressive:
- It should capture more opportunity when ASH is moving or when quotes are stale, at the cost of more trading and potentially worse adverse selection.
