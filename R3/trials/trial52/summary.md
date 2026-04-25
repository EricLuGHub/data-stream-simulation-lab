# Trial 52 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_voucher_only
- Status: ok
- Overall rank: 45
- Set rank: 5

## PnL Metrics

- Total PnL (days 0+1): -600.50
- Day 0 PnL: -7909.00
- Day 1 PnL: 7308.50
- Max drawdown proxy: 87948.50
- Score used for ranking: -31426.96
- Curve step volatility: 889.66

## Strategy Parameters

- edge_mult: 0.85
- join_size: 12
- max_take_mid: 14
- max_take_wing: 8
- sigma_scale: 1.05
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
- Mixed finding: losses are contained compared with most voucher variants, suggesting promising structure but poor edge calibration.
- Generalization finding: day-level sign flip indicates regime sensitivity and weaker robustness.
- Relative placement: overall rank #45 and set rank #5 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
