# Trial 16 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_balanced
- Status: ok
- Overall rank: 18
- Set rank: 18

## PnL Metrics

- Total PnL (days 0+1): 7062.00
- Day 0 PnL: 2462.00
- Day 1 PnL: 4600.00
- Max drawdown proxy: 13049.00
- Score used for ranking: 2489.15
- Curve step volatility: 114.01

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.2
- make_edge: 1.6
- max_take: 14
- quote_size: 16
- signal_gate: 0.02
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Relative placement: overall rank #18 and set rank #18 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
