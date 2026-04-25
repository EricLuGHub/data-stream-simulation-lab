# Trial 38 Summary

## Strategy

- Set: PACK_ONLY
- Family: pack_aggressive
- Status: ok
- Overall rank: 40
- Set rank: 40

## PnL Metrics

- Total PnL (days 0+1): 4165.00
- Day 0 PnL: 1451.00
- Day 1 PnL: 2714.00
- Max drawdown proxy: 15665.00
- Score used for ranking: -1324.96
- Curve step volatility: 144.22

## Strategy Parameters

- ema_alpha: 0.12
- inventory_skew: 0.9
- make_edge: 1.3
- max_take: 18
- quote_size: 20
- signal_gate: 0.01
- signal_weight: 1.6
- take_edge: 1.4

## Notes And Findings

- This is a PACK-only microstructure strategy combining fair-value EMA with order-book imbalance signals.
- Mixed finding: strategy is profitable but weaker than top PACK variants; likely needs threshold/inventory tuning.
- Risk finding: drawdown is elevated for this setup, indicating inventory stress or late-session adverse fills.
- Relative placement: overall rank #40 and set rank #40 in the evaluated leaderboard.
- Parameter takeaway: refine around make/take edge and inventory skew first; these are typically the dominant PnL levers for PACK runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
