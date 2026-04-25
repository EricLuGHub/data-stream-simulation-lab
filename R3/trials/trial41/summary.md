# Trial 41 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_hybrid
- Status: ok
- Overall rank: 60
- Set rank: 20

## PnL Metrics

- Total PnL (days 0+1): -139770.50
- Day 0 PnL: -67120.00
- Day 1 PnL: -72650.50
- Max drawdown proxy: 164430.50
- Score used for ranking: -197353.75
- Curve step volatility: 651.44

## Strategy Parameters

- edge_mult: 0.85
- join_size: 14
- max_take_mid: 16
- max_take_wing: 10
- sigma_scale: 0.9
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
- Relative placement: overall rank #60 and set rank #20 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
