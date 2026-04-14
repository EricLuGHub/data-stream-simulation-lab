
v4 added hard inventory limits for ASH (suppress one side at |pos|>30) and position gating + trend_edge for Pepper (suppress sells when far below target, shift FV up to buy more aggressively).

Results vs trial3:
- ASH: 1165 (slightly down from 1226). Hard limit worked well — max position 29, final -6 (much better than +23 in trial3). Spread capture steady at 5.4/unit.
- PEPPER: 3763 (up 88% from 2006). Position gating prevented the early short blowup. Built to +32 by t=40K. BUT then bled to -21 by end — went short a trending-up asset in second half.
- Root cause: max_timestamp=999900 but backtest runs only 99900. Progress calc thinks we're at 5-10% of day, so target stays ~38 throughout. gap_threshold=15 was too loose — sells not suppressed until position drops to ~23, leaving a 15-unit erosion window.
- Total: 4928 (up from 3232, +52%)

Extended ASH analysis findings (analysis_ash.ipynb points 3-6):
- Regime behavior: edge varies 0.6-3.7 across time buckets, non-stationary
- Inventory sim: ~9000 PnL/day with simple ±3 inv. Our 1165/0.1 day is roughly proportional.
- Threshold sweep: threshold=4-5 gives 1.6-2.0 edge, threshold=2 at horizon=10+ gives best freq/edge balance
- Validation: rolling FV gives highest edge (1.7-1.9), leave-one-day-out confirms FV shifts across days

Proposed next steps:
- PEPPER: tighten gap_threshold (15→5) so sells suppressed unless within 5 of target. Effectively buy-and-hold with target ~38 throughout backtest. Increase trend_edge 4→5.
- ASH: keep current approach, parameters are solid

PNL: 4928
