# Trial 21 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_balanced
- Status: ok
- Overall rank: 7
- Set rank: 7

## PnL Metrics

- Total PnL (days 0+1): 8413.00
- Day 0 PnL: 2750.00
- Day 1 PnL: 5663.00
- Max drawdown proxy: 10130.00
- Score used for ranking: 4861.69
- Curve step volatility: 116.21

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.2
- make_edge: 1.6
- max_take: 14
- quote_size: 16
- signal_gate: 0.02
- signal_weight: 0.8
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Strong initial finding: this parameterization is one of the better PACK candidates and is worth carrying to refinement.
- Relative placement: overall rank #7 and set rank #7 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
