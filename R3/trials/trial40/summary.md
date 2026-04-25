# Trial 40 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_unconventional
- Status: ok
- Overall rank: 38
- Set rank: 38

## PnL Metrics

- Total PnL (days 0+1): 4851.00
- Day 0 PnL: 1489.00
- Day 1 PnL: 3362.00
- Max drawdown proxy: 14974.00
- Score used for ranking: -396.99
- Curve step volatility: 141.89

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 1.5
- make_edge: 1.5
- max_take: 16
- quote_size: 18
- signal_gate: 0.0
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Mixed finding: strategy is profitable but weaker than top PACK variants; likely needs threshold/inventory tuning.
- Relative placement: overall rank #38 and set rank #38 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
