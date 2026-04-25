# Trial 37 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_conservative
- Status: ok
- Overall rank: 23
- Set rank: 23

## PnL Metrics

- Total PnL (days 0+1): 6375.00
- Day 0 PnL: 2460.00
- Day 1 PnL: 3915.00
- Max drawdown proxy: 13890.00
- Score used for ranking: 1506.43
- Curve step volatility: 141.40

## Strategy Parameters

- ema_alpha: 0.12
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
- Relative placement: overall rank #23 and set rank #23 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
