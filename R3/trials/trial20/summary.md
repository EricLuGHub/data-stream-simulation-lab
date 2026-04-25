# Trial 20 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_unconventional
- Status: ok
- Overall rank: 16
- Set rank: 16

## PnL Metrics

- Total PnL (days 0+1): 7311.00
- Day 0 PnL: 2733.00
- Day 1 PnL: 4578.00
- Max drawdown proxy: 12100.00
- Score used for ranking: 3070.59
- Curve step volatility: 108.25

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.5
- make_edge: 1.5
- max_take: 16
- quote_size: 18
- signal_gate: 0.0
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #16 and set rank #16 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
