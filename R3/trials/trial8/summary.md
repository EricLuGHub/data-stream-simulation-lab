# Trial 8 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_aggressive
- Status: ok
- Overall rank: 27
- Set rank: 27

## PnL Metrics

- Total PnL (days 0+1): 6689.00
- Day 0 PnL: 1985.00
- Day 1 PnL: 4704.00
- Max drawdown proxy: 15803.00
- Score used for ranking: 1151.97
- Curve step volatility: 119.62

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 0.9
- make_edge: 1.3
- max_take: 18
- quote_size: 20
- signal_gate: 0.01
- signal_weight: 0.8
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #27 and set rank #27 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
