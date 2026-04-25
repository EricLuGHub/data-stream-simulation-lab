# Trial 33 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_aggressive
- Status: ok
- Overall rank: 39
- Set rank: 39

## PnL Metrics

- Total PnL (days 0+1): 4368.00
- Day 0 PnL: 1700.00
- Day 1 PnL: 2668.00
- Max drawdown proxy: 14144.00
- Score used for ranking: -589.42
- Curve step volatility: 140.46

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 0.9
- make_edge: 1.3
- max_take: 18
- quote_size: 20
- signal_gate: 0.01
- signal_weight: 1.6
- take_edge: 0.8

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Mixed finding: strategy is profitable but weaker than top PACK variants; likely needs threshold/inventory tuning.
- Relative placement: overall rank #39 and set rank #39 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
