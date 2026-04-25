# VV_XXXX findings

Day 2 is excluded from this analysis to keep it held out for later backtest validation.

Round 3 context from the design doc: the VEV series are velvetfruit extract vouchers, i.e. options on VELVETFRUIT_EXTRACT. Historical day 2 corresponds to a lower time-to-expiry than days 0 and 1, so holding it out avoids leaking late-expiry behavior into the exploratory read.

Key strike-level findings from days 0 and 1:

- VEV_4000 is the most active voucher in the local data slice, with 336 trades, mean mid 1,247.47, mean spread 20.77, and the strongest imbalance-to-next-mid correlation at about +0.48.
- VEV_5300, VEV_5400, and VEV_5500 also have meaningful coverage and show gradually smaller mid levels and spreads as strike rises.
- VEV_4500, VEV_5000, and VEV_5100 have very thin trade coverage in this slice, so any signal there should be treated cautiously.
- VEV_6000 and VEV_6500 are effectively flat at a 0.5 mid with spread 1.0 and no useful directional structure in the two in-sample days.

New diagnostics (from expanded notebook analysis):

- Underlying linkage is monotone in strike via delta-slope proxy (`dVV` regressed on `dVELV`):
	- around 0.75 at `VEV_4000`, tapering to around 0.06 by `VEV_5500`, and ~0 at `VEV_6000`/`VEV_6500`.
- Time-value proxy (`voucher_mid - max(VELV_mid - strike, 0)`) peaks near the near-money strikes:
	- highest around `VEV_5200` (~48.85) and `VEV_5300` (~47.90), then drops away on both sides.
- Tradability score (activity + movement + imbalance signal - pinned penalty) ranks:
	1) `VEV_4000`, 2) `VEV_5500`, 3) `VEV_5400`, 4) `VEV_5300`.
- Even when `VEV_6000` and `VEV_6500` have many prints, they remain pinned (delta ~0), so they are poor candidates for directional alpha.

Takeaway: the voucher family has a clear pattern now: model per-strike with a strong preference for `VEV_4000`/`VEV_5400`/`VEV_5500`/`VEV_5300`, and treat the deepest OTM strikes as mostly static boundary instruments rather than predictive alpha sources.