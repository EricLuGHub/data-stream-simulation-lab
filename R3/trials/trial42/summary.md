# Trial 42 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_voucher_only
- Status: ok
- Overall rank: 44
- Set rank: 4

## PnL Metrics

- Total PnL (days 0+1): 12949.00
- Day 0 PnL: 2527.00
- Day 1 PnL: 10422.00
- Max drawdown proxy: 49811.50
- Score used for ranking: -4516.13
- Curve step volatility: 622.17

## Strategy Parameters

- edge_mult: 0.85
- join_size: 12
- max_take_mid: 14
- max_take_wing: 8
- sigma_scale: 0.9
- tau_scale: 250.0
- traded_list: ['VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_6000']
- velv_ema_alpha: 0.06
- velv_enable: False
- velv_make_edge: 1.9
- velv_signal_gate: 0.03
- velv_signal_weight: 1.0
- velv_take_edge: 1.2

## Notes And Findings

- This is a VELV/VEV option-smile strategy using Black-Scholes fair values with strike-level controls.
- Positive finding: this variant has the strongest voucher-set PnL among current runs and should be prioritized for second-stage tuning.
- Generalization finding: both day 0 and day 1 were positive, indicating better split robustness.
- Relative placement: overall rank #44 and set rank #4 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
