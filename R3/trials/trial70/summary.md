# Trial 70 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_regime_mix
- Status: ok
- Overall rank: 71
- Set rank: 31

## PnL Metrics

- Total PnL (days 0+1): -228874.00
- Day 0 PnL: -98312.00
- Day 1 PnL: -130562.00
- Max drawdown proxy: 248030.50
- Score used for ranking: -315730.31
- Curve step volatility: 912.72

## Strategy Parameters

- edge_mult: 1.1
- join_size: 16
- max_take_mid: 18
- max_take_wing: 10
- sigma_scale: 0.9
- tau_scale: 320.0
- traded_list: ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500', 'VEV_6000', 'VEV_6500']
- velv_ema_alpha: 0.1
- velv_enable: True
- velv_make_edge: 1.6
- velv_signal_gate: 0.02
- velv_signal_weight: 1.6
- velv_take_edge: 1.1

## Notes And Findings

- This is a VELV/VEV option-smile strategy using Black-Scholes fair values with strike-level controls.
- Negative finding: substantial losses suggest over-aggressive cross/quote behavior or mis-calibrated smile assumptions.
- Generalization finding: losses on both days indicate this configuration is not robust enough to keep.
- Relative placement: overall rank #71 and set rank #31 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
