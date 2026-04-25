# VV_XXXX findings

Day 2 is excluded from this analysis to keep it held out for later backtest validation.

Round 3 context from the design doc: the VEV series are velvetfruit extract vouchers, i.e. options on VELVETFRUIT_EXTRACT. Historical day 2 corresponds to a lower time-to-expiry than days 0 and 1, so holding it out avoids leaking late-expiry behavior into the exploratory read.

Key strike-level findings from days 0 and 1:

- VEV_4000 is the most active voucher in the local data slice, with 336 trades, mean mid 1,247.47, mean spread 20.77, and the strongest imbalance-to-next-mid correlation at about +0.48.
- VEV_5300, VEV_5400, and VEV_5500 also have meaningful coverage and show gradually smaller mid levels and spreads as strike rises.
- VEV_4500, VEV_5000, and VEV_5100 have very thin trade coverage in this slice, so any signal there should be treated cautiously.
- VEV_6000 and VEV_6500 are effectively flat at a 0.5 mid with spread 1.0 and no useful directional structure in the two in-sample days.

Takeaway: the voucher family is highly strike-sensitive. The lower strikes carry the most structure and the clearest microstructure signal, while the far OTM strikes look pinned and should not be over-interpreted from the current in-sample window.