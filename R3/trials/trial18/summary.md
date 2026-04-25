# Trial 18 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_aggressive
- Status: ok
- Overall rank: 14
- Set rank: 14

## PnL Metrics

- Total PnL (days 0+1): 7383.00
- Day 0 PnL: 2568.00
- Day 1 PnL: 4815.00
- Max drawdown proxy: 11588.00
- Score used for ranking: 3321.98
- Curve step volatility: 104.33

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 0.9
- make_edge: 1.3
- max_take: 18
- quote_size: 20
- signal_gate: 0.01
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #14 and set rank #14 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
