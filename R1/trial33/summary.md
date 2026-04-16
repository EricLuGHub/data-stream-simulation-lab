# Trial 33: Late-Carry Boosted Participation Model

## Hypothesis
Most remaining gap came from late-session under-exposure; keep more carry in buckets 7-9 while preserving selective de-risk on true overextension.

## Key design points
- PEPPER-only (`INTARIAN_PEPPER_ROOT`)
- Based on trial32 participation logic
- Higher late-bucket target inventory
- Slightly stricter upside overextension trigger before scaling out
- Strong sell suppression while trend remains constructive

## Backtest (Round 1, all days)
- Day -2: 45,310
- Day -1: 44,235
- Day 0: 41,013
- Total: 130,558

Risk metrics:
- Sharpe: 19.4621
- Max drawdown abs: 634,900
- Calmar: 0.2056

## Notes
New best local PEPPER-only result in this repo so far, exceeding trial23 and trial5.
