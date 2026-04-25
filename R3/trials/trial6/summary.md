# Trial 6 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_balanced
- Status: ok
- Overall rank: 32
- Set rank: 32

## PnL Metrics

- Total PnL (days 0+1): 6289.00
- Day 0 PnL: 2355.00
- Day 1 PnL: 3934.00
- Max drawdown proxy: 16072.00
- Score used for ranking: 657.84
- Curve step volatility: 119.24

## Strategy Parameters

- ema_alpha: 0.05
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
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #32 and set rank #32 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
