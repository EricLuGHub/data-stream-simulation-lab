# Trial 18: Trial14 ASH + PEPPER Trend Merge

Approach:
- ASH_COATED_OSMIUM:
  - Reuses Trial 14's passive inventory-aware market-making logic.
  - Slow EMA + wall-mid + imbalance fair value blend.
  - Conservative quoting and strong inventory skew at stretched states.
- INTARIAN_PEPPER_ROOT:
  - Uses anchored trend fair value (anchor + linear slope) blended with EMA.
  - Adds trend edge and a time-varying long target.
  - Position gating suppresses the wrong-side quotes when far from target.

Goal:
- Keep the proven ASH baseline behavior from Trial 14.
- Add explicit PEPPER trend capture instead of leaving PEPPER unused.
