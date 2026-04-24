# R2 Trial 4 - Trial14 Tuned (Lower-Risk)

Tuned on round2 days -1 and 0, then validated on day 1.

- Best training total (2--1, 2-0): **21,777**
- Holdout day 1 (2-1): **10,777**
- Full round 2 total: **32,554**
- Daily PnL: day -1=10,714, day 0=11,063, day 1=10,777
- Best params: {'EMA_ALPHA': 0.26, 'EMA_DECAY': 0.74, 'HIST_LEN': 40, 'SHORT_LEN': 9, 'LONG_LEN': 22, 'WALL_MIN': 11, 'WALL_WEIGHT': 0.53, 'EMA_WEIGHT': 0.27, 'TREND_WEIGHT': 0.2, 'IMB_WEIGHT': 0.5, 'TAKE_WIDTH': 1, 'TAKE_Z_RELAX': 1.1, 'TAKE_CAP': 5, 'HALF_SPREAD_LO': 3, 'HALF_SPREAD_HI': 4, 'SPREAD_CUTOFF': 11, 'INV_SKEW': 3.6, 'IMPROVE_GAP': 2, 'BASE_SIZE': 15, 'BUY_BIAS': 0.75, 'SELL_BIAS': 0.72, 'FORCE_POS': 34, 'FORCE_Z': 1.7, 'FORCE_EXTRA': 7}
- Strategy file: r2_ash_trial14_tuned.py
