# Trial 35 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_unconventional
- Status: ok
- Overall rank: 35
- Set rank: 35

## PnL Metrics

- Total PnL (days 0+1): 5092.00
- Day 0 PnL: 1715.00
- Day 1 PnL: 3377.00
- Max drawdown proxy: 13131.00
- Score used for ranking: 489.35
- Curve step volatility: 136.10

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.5
- make_edge: 1.5
- max_take: 16
- quote_size: 18
- signal_gate: 0.0
- signal_weight: 1.6
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #35 and set rank #35 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
