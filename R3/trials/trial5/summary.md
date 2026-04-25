# Trial 5 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_unconventional
- Status: ok
- Overall rank: 28
- Set rank: 28

## PnL Metrics

- Total PnL (days 0+1): 6274.00
- Day 0 PnL: 2092.00
- Day 1 PnL: 4182.00
- Max drawdown proxy: 14721.00
- Score used for ranking: 1116.20
- Curve step volatility: 108.91

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.5
- make_edge: 1.5
- max_take: 16
- quote_size: 18
- signal_gate: 0.0
- signal_weight: 0.8
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #28 and set rank #28 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
