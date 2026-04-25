# Trial 92 Summary

## Strategy

- Set: MERGED_PACK_VELV_VEV
- Family: merge_trial24_trial72
- Status: ok
- Overall rank: 1
- Set rank: 1

## PnL Metrics

- Total PnL (days 0+1): 31053.00
- Day 0 PnL: 7307.00
- Day 1 PnL: 23746.00
- Max drawdown proxy: 61901.00
- Score used for ranking: 9357.86
- Curve step volatility: 595.77

## Strategy Parameters

- pack: {'ema_alpha': 0.12, 'signal_weight': 0.8, 'take_edge': 0.8, 'make_edge': 2.2, 'inventory_skew': 2.2, 'signal_gate': 0.05, 'max_take': 10, 'quote_size': 12}
- voucher: {'tau_scale': 320.0, 'sigma_scale': 1.05, 'edge_mult': 0.85, 'join_size': 12, 'max_take_wing': 8, 'max_take_mid': 14, 'traded_list': ['VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_6000']}

## Notes And Findings

- Relative placement: overall rank #1 and set rank #1 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
