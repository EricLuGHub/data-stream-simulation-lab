# VELV findings

Day 2 is excluded from this analysis to keep it held out for later backtest validation.

- Product: VELVETFRUIT_EXTRACT
- Coverage used: days 0 and 1 only
- Price rows: 20,000
- Trade rows: 895
- Mean mid: 5,247.45
- Mid standard deviation: 14.18
- Mean spread: 4.99
- Daily mid change: day 0 = -6, day 1 = +20.5
- Trade VWAP: 5,246.57
- Mean trade-vs-mid edge: +0.09
- Mean imbalance-to-next-mid correlation: +0.28

New diagnostics (from expanded notebook analysis):

- Imbalance event study is strong and symmetric:
	- `low_imbalance` avg next move: -0.460
	- `high_imbalance` avg next move: +0.552
	- `mid_imbalance` avg next move: about -0.010
- Mean-reversion proxy: AR(1) beta on next mid changes is -0.160 (clearer short-horizon reversal than PACK).
- Spread-to-volatility relation is informative: lower spread states (1-3) coincide with larger absolute next moves than spread 5-6, suggesting spread is not a pure risk proxy here.
- Intraday profile is very stable:
	- abs next move roughly 0.83 to 0.90
	- spread roughly 4.93 to 5.05
- Signed trade-flow proxy has only weak positive relation to next move (corr about +0.063).

Takeaway: VELV now shows the cleanest pattern among the three product families: stable intraday structure, measurable short-horizon mean reversion, and a strong extreme-imbalance directional effect. This is the best candidate for a simple, robust first predictive model.