# Trial 19 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_lowrisk
- Status: ok
- Overall rank: 2
- Set rank: 2

## PnL Metrics

- Total PnL (days 0+1): 9371.00
- Day 0 PnL: 4345.00
- Day 1 PnL: 5026.00
- Max drawdown proxy: 9056.00
- Score used for ranking: 6196.15
- Curve step volatility: 104.94

## Strategy Parameters

- ema_alpha: 0.05
- inventory_skew: 2.2
- make_edge: 2.2
- max_take: 10
- quote_size: 12
- signal_gate: 0.05
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Strong initial finding: this parameterization is one of the better PACK candidates and is worth carrying to refinement.
- Risk finding: drawdown is controlled relative to peers, suggesting good inventory discipline.
- Relative placement: overall rank #2 and set rank #2 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
