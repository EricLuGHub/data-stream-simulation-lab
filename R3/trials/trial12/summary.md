# Trial 12 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_conservative
- Status: ok
- Overall rank: 36
- Set rank: 36

## PnL Metrics

- Total PnL (days 0+1): 6405.00
- Day 0 PnL: 2329.00
- Day 1 PnL: 4076.00
- Max drawdown proxy: 17427.00
- Score used for ranking: 297.05
- Curve step volatility: 169.95

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 1.8
- make_edge: 1.9
- max_take: 12
- quote_size: 14
- signal_gate: 0.03
- signal_weight: 1.6
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Positive finding: strategy is profitable and stable enough to remain in contention for top-pack selection.
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #36 and set rank #36 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
