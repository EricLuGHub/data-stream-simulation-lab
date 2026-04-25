# Trial 22 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_conservative
- Status: ok
- Overall rank: 3
- Set rank: 3

## PnL Metrics

- Total PnL (days 0+1): 9427.00
- Day 0 PnL: 3198.00
- Day 1 PnL: 6229.00
- Max drawdown proxy: 9593.00
- Score used for ranking: 6063.79
- Curve step volatility: 113.25

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.8
- make_edge: 1.9
- max_take: 12
- quote_size: 14
- signal_gate: 0.03
- signal_weight: 0.8
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Strong initial finding: this parameterization is one of the better PACK candidates and is worth carrying to refinement.
- Risk finding: drawdown is controlled relative to peers, suggesting good inventory discipline.
- Relative placement: overall rank #3 and set rank #3 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
