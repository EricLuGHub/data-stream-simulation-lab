# Trial 29 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_lowrisk
- Status: ok
- Overall rank: 5
- Set rank: 5

## PnL Metrics

- Total PnL (days 0+1): 9138.00
- Day 0 PnL: 3124.00
- Day 1 PnL: 6014.00
- Max drawdown proxy: 10337.00
- Score used for ranking: 5514.32
- Curve step volatility: 114.60

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 2.2
- make_edge: 2.2
- max_take: 10
- quote_size: 12
- signal_gate: 0.05
- signal_weight: 0.8
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Strong initial finding: this parameterization is one of the better PACK candidates and is worth carrying to refinement.
- Relative placement: overall rank #5 and set rank #5 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
