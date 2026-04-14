
This iteration fixed the main v1 bug: hardcoded trend_start=13000 for Pepper Root when actual price started at ~12000.
Now anchors on first observed mid price and projects forward with the known +0.001/tick slope.
Also tightened ASH make_spread from 2 to 1 and increased make_size from 25 to 40.

Results vs trial1:
- ASH: 904 (down from 988). Tighter spread hurt per-unit profit (3.8 vs 5.1 capture). Net position 27 = inventory buildup.
- PEPPER: 1778 (up from 1110). 48 trades vs 9. Anchoring fix eliminated the -3800 PnL spike at t=0. But position oscillated instead of riding the trend.
- Total: 2682 (up from 2098, +28%)

Proposed next steps:
- ASH: revert make_spread to 2, increase position_skew to reduce inventory accumulation
- PEPPER: implement time-varying position target (long early, flatten late) to capture trend profit on top of spread profit
- look into L3 order book files for more granular info

PNL: 2682
