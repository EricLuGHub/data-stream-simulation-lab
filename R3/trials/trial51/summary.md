# Trial 51 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_hybrid
- Status: ok
- Overall rank: 61
- Set rank: 21

## PnL Metrics

- Total PnL (days 0+1): -153606.00
- Day 0 PnL: -77792.00
- Day 1 PnL: -75814.00
- Max drawdown proxy: 182238.50
- Score used for ranking: -217435.31
- Curve step volatility: 916.72

## Strategy Parameters

- edge_mult: 0.85
- join_size: 14
- max_take_mid: 16
- max_take_wing: 10
- sigma_scale: 1.05
- tau_scale: 250.0
- traded_list: ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_6000', 'VEV_6500']
- velv_ema_alpha: 0.08
- velv_enable: True
- velv_make_edge: 1.8
- velv_signal_gate: 0.02
- velv_signal_weight: 1.4
- velv_take_edge: 1.3

## Notes And Findings

- This is a VELV/VEV option-smile strategy using Black-Scholes fair values with strike-level controls.
- Negative finding: substantial losses suggest over-aggressive cross/quote behavior or mis-calibrated smile assumptions.
- Generalization finding: losses on both days indicate this configuration is not robust enough to keep.
- Relative placement: overall rank #61 and set rank #21 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
