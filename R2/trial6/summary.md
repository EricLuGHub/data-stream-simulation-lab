# R2 Trial 6 - ASH Max-Profit Tuned

Tuned on round2 days -1 and 0, validated on day 1.

- Best training total: **12,392**
- Holdout day 1: **5058**
- Full round 2 total: **17450**
- Daily PnL: day -1=6137, day 0=6255, day 1=5058
- Strategy file: r2_ash_maxprofit_tuned.py
- Best params: {'EMA_ALPHA': 0.26, 'HIST_LEN': 52, 'SHORT_LEN': 10, 'LONG_LEN': 26, 'WALL_MIN': 11, 'WALL_W': 0.52, 'EMA_W': 0.28, 'TREND_W': 0.2, 'IMB_W': 0.5, 'TARGETS': '36.0, 36.0, 35.0, 34.0, 32.0, 31.0, 31.0, 37.0, 40.0, 41.0', 'SLOPE_UP_TRIG': 0.8, 'SLOPE_DN_TRIG': 0.7, 'SLOPE_UP_ADD': 4.0, 'SLOPE_DN_SUB': 2.0, 'Z_BUY_TRIG': 1.2, 'Z_SELL_TRIG': 1.8, 'Z_BUY_ADD': 4.0, 'Z_SELL_SUB': 3.0, 'TAKE_WIDTH': 1, 'TAKE_Z_TIGHTEN': 1.3, 'TAKE_CAP_BASE': 6, 'TAKE_CAP_PART': 4, 'CARRY_T1': 0.42, 'CARRY_T2': 0.7, 'CARRY_S1': 0.45, 'CARRY_S2': 0.65, 'CARRY_F1': 32, 'CARRY_F2': 42, 'UNWIND_Z': 2.4, 'UNWIND_SLOPE': 0.55, 'UNWIND_GAP': 6, 'UNWIND_CAP': 8, 'HALF_LO': 2, 'HALF_HI': 3, 'SPREAD_CUTOFF': 12, 'INV_SKEW': 4.6, 'SLOPE_PX': 0.2, 'IMPROVE_GAP': 1, 'BUY_BASE': 26, 'SELL_BASE': 21, 'BUY_PART': 8, 'SELL_PART': 4, 'BUY_INV_W': 1.0, 'SELL_INV_W': 1.0, 'SUPPRESS_SELL_SLOPE': 0.65, 'SUPPRESS_SELL_GAP': 2, 'SUPPRESS_SELL_Z': 0.65, 'SUPPRESS_BUY_SLOPE': 1.0, 'SUPPRESS_BUY_GAP': 8, 'SUPPRESS_BUY_Z': 0.2}
