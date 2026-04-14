
v3 reverted ASH make_spread to 2 (fixing the v2 regression) and added time-varying position targets for Pepper.

Results vs trial2:
- ASH: 1226 (up from 904). Spread capture back to 5.3/unit (was 3.8). But net position still 23 — inventory problem persists despite position_skew=2.5.
- PEPPER: 2006 (up from 1778). But went SHORT to -15 in first 30K timestamps despite target=+40. Market took our asks faster than our bids. Time-varying target biased quotes correctly but couldn't control which side filled.
- Total: 3232 (up from 2682, +20%)

New ASH analysis findings (updated analysis_ash.ipynb):
- deviation_ar1_beta=1.0 → ASH is a pure random walk, not mean-reverting to fixed level
- cheap_edge_net=-15 → zero edge after spread costs, profit is 100% passive market making
- return_autocorr=-0.5 → bid-ask bounce, favorable for market makers

Proposed next steps:
- ASH: hard inventory limit at |pos| > 30 — suppress the accumulating side entirely
- PEPPER: suppress sell orders when position is far below target (position gating), add trend_edge to FV so we're willing to pay above mid to get long faster

PNL: 3232
