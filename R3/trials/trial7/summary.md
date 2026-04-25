# Trial 7 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_conservative
- Status: ok
- Overall rank: 33
- Set rank: 33

## PnL Metrics

- Total PnL (days 0+1): 6294.00
- Day 0 PnL: 2592.00
- Day 1 PnL: 3702.00
- Max drawdown proxy: 16111.00
- Score used for ranking: 649.18
- Curve step volatility: 119.37

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.8
- make_edge: 1.9
- max_take: 12
- quote_size: 14
- signal_gate: 0.03
- signal_weight: 0.8
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #33 and set rank #33 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
