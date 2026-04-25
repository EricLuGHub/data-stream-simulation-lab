# Trial 26 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_balanced
- Status: ok
- Overall rank: 17
- Set rank: 17

## PnL Metrics

- Total PnL (days 0+1): 7188.00
- Day 0 PnL: 1491.00
- Day 1 PnL: 5697.00
- Max drawdown proxy: 12894.00
- Score used for ranking: 2668.27
- Curve step volatility: 136.55

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.2
- make_edge: 1.6
- max_take: 14
- quote_size: 16
- signal_gate: 0.02
- signal_weight: 0.8
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #17 and set rank #17 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
