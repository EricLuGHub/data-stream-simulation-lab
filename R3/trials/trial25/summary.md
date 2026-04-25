# Trial 25 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_unconventional
- Status: ok
- Overall rank: 9
- Set rank: 9

## PnL Metrics

- Total PnL (days 0+1): 8155.00
- Day 0 PnL: 2616.00
- Day 1 PnL: 5539.00
- Max drawdown proxy: 10080.00
- Score used for ranking: 4621.31
- Curve step volatility: 113.83

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.5
- make_edge: 1.5
- max_take: 16
- quote_size: 18
- signal_gate: 0.0
- signal_weight: 0.8
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Strong initial finding: this parameterization is one of the better PACK candidates and is worth carrying to refinement.
- Relative placement: overall rank #9 and set rank #9 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
