# Trial 17 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_conservative
- Status: ok
- Overall rank: 15
- Set rank: 15

## PnL Metrics

- Total PnL (days 0+1): 7458.00
- Day 0 PnL: 3156.00
- Day 1 PnL: 4302.00
- Max drawdown proxy: 12105.00
- Score used for ranking: 3215.88
- Curve step volatility: 107.46

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.8
- make_edge: 1.9
- max_take: 12
- quote_size: 14
- signal_gate: 0.03
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #15 and set rank #15 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
