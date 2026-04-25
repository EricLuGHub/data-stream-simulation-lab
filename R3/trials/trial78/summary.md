# Trial 78 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_highrisk
- Status: ok
- Overall rank: 74
- Set rank: 34

## PnL Metrics

- Total PnL (days 0+1): -248195.50
- Day 0 PnL: -126629.00
- Day 1 PnL: -121566.50
- Max drawdown proxy: 265515.00
- Score used for ranking: -341156.72
- Curve step volatility: 619.43

## Strategy Parameters

- edge_mult: 1.1
- join_size: 18
- max_take_mid: 20
- max_take_wing: 12
- sigma_scale: 1.05
- tau_scale: 320.0
- traded_list: ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500', 'VEV_6000', 'VEV_6500']
- velv_ema_alpha: 0.11
- velv_enable: True
- velv_make_edge: 1.5
- velv_signal_gate: 0.01
- velv_signal_weight: 1.8
- velv_take_edge: 1.0

## Notes And Findings

- This is a VELV/VEV option-smile strategy using Black-Scholes fair values with strike-level controls.
- Negative finding: substantial losses suggest over-aggressive cross/quote behavior or mis-calibrated smile assumptions.
- Generalization finding: losses on both days indicate this configuration is not robust enough to keep.
- Relative placement: overall rank #74 and set rank #34 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
