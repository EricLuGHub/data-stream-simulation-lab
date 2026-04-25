# PACK findings

Day 2 is excluded from this analysis to keep it held out for later backtest validation.

- Product: HYDROGEL_PACK
- Coverage used: days 0 and 1 only
- Price rows: 20,000
- Trade rows: 699
- Mean mid: 9,991.51
- Mid standard deviation: 32.07
- Mean spread: 15.71
- Daily mid change: day 0 = -42, day 1 = +57
- Trade VWAP: 9,992.41
- Mean trade-vs-mid edge: +0.17
- Mean imbalance-to-next-mid correlation: +0.30

New diagnostics (from expanded notebook analysis):

- Imbalance event study (robust buckets):
	- `low_imbalance` avg next move: -3.90
	- `high_imbalance` avg next move: +4.09
	- `mid_imbalance` avg next move: about 0.00
- Mean-reversion proxy: AR(1) beta on next mid changes is -0.131 (mild short-horizon reversal).
- Spread regime is mostly stable around 15-16, but the rare wider-spread regime (17) has higher next-step absolute move (1.79 vs 1.66).
- Intraday diagnostics are fairly flat (abs next move roughly 1.59 to 1.74), so there is no strong time-of-day edge in days 0-1.
- Signed trade-flow proxy has near-zero linear relation to the next move (corr about -0.007), so order-book imbalance is currently the better directional feature.

Takeaway: PACK has a usable directional microstructure signal, but it is concentrated in imbalance extremes rather than smooth linear flow. For modeling, treat it as an "extreme-state" signal product with mild reversion and mostly stable intraday behavior.