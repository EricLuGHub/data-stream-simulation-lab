# Trial 2 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_conservative
- Status: ok
- Overall rank: 20
- Set rank: 20

## PnL Metrics

- Total PnL (days 0+1): 6985.00
- Day 0 PnL: 2350.00
- Day 1 PnL: 4635.00
- Max drawdown proxy: 14576.00
- Score used for ranking: 1877.81
- Curve step volatility: 111.75

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.8
- make_edge: 1.9
- max_take: 12
- quote_size: 14
- signal_gate: 0.03
- signal_weight: 0.8
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #20 and set rank #20 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
