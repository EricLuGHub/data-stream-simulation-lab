# Trial 59 Summary

## Strategy

- Set: VELV_VEV_TARGET
- Family: smile_lowrisk
- Status: ok
- Overall rank: 54
- Set rank: 14

## PnL Metrics

- Total PnL (days 0+1): -94209.50
- Day 0 PnL: -45495.00
- Day 1 PnL: -48714.50
- Max drawdown proxy: 143848.00
- Score used for ranking: -144601.99
- Curve step volatility: 913.87

## Strategy Parameters

- edge_mult: 1.1
- join_size: 10
- max_take_mid: 12
- max_take_wing: 8
- sigma_scale: 1.05
- tau_scale: 250.0
- traded_list: ['VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500', 'VEV_6000']
- velv_ema_alpha: 0.07
- velv_enable: True
- velv_make_edge: 2.2
- velv_signal_gate: 0.04
- velv_signal_weight: 1.1
- velv_take_edge: 1.6

## Notes And Findings

- This is a VELV/VEV option-smile strategy using Black-Scholes fair values with strike-level controls.
- Negative finding: substantial losses suggest over-aggressive cross/quote behavior or mis-calibrated smile assumptions.
- Generalization finding: losses on both days indicate this configuration is not robust enough to keep.
- Relative placement: overall rank #54 and set rank #14 in the evaluated leaderboard.
- Parameter takeaway: refine around edge multiplier, tau scale, and sigma scale first; these are typically the dominant levers for voucher runs.

## Next Action

- Keep this trial as a baseline record and compare against refined descendants in phase-2 runs.
