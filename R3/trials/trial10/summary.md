# Trial 10 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_unconventional
- Status: ok
- Overall rank: 24
- Set rank: 24

## PnL Metrics

- Total PnL (days 0+1): 6687.00
- Day 0 PnL: 2365.00
- Day 1 PnL: 4322.00
- Max drawdown proxy: 15093.00
- Score used for ranking: 1398.79
- Curve step volatility: 113.12

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.5
- make_edge: 1.5
- max_take: 16
- quote_size: 18
- signal_gate: 0.0
- signal_weight: 0.8
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #24 and set rank #24 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
