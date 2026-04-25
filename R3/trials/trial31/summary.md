# Trial 31 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_balanced
- Status: ok
- Overall rank: 31
- Set rank: 31

## PnL Metrics

- Total PnL (days 0+1): 5441.00
- Day 0 PnL: 1916.00
- Day 1 PnL: 3525.00
- Max drawdown proxy: 13463.00
- Score used for ranking: 721.77
- Curve step volatility: 143.64

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.2
- make_edge: 1.6
- max_take: 14
- quote_size: 16
- signal_gate: 0.02
- signal_weight: 1.6
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #31 and set rank #31 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
