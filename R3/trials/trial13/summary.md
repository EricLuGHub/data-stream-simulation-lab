# Trial 13 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_aggressive
- Status: ok
- Overall rank: 26
- Set rank: 26

## PnL Metrics

- Total PnL (days 0+1): 6846.00
- Day 0 PnL: 2001.00
- Day 1 PnL: 4845.00
- Max drawdown proxy: 15967.00
- Score used for ranking: 1249.38
- Curve step volatility: 163.30

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 0.9
- make_edge: 1.3
- max_take: 18
- quote_size: 20
- signal_gate: 0.01
- signal_weight: 1.6
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #26 and set rank #26 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
