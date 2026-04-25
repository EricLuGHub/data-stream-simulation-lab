# Trial 36 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_balanced
- Status: ok
- Overall rank: 37
- Set rank: 37

## PnL Metrics

- Total PnL (days 0+1): 5092.00
- Day 0 PnL: 1648.00
- Day 1 PnL: 3444.00
- Max drawdown proxy: 15624.00
- Score used for ranking: -383.92
- Curve step volatility: 150.33

## Strategy Parameters

- ema_alpha: 0.12
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
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #37 and set rank #37 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
