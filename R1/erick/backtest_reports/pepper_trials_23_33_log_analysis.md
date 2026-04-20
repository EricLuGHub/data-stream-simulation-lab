# PEPPER Log Analysis: Trials 23 vs 33

Method:
- Parsed `Activities log` from each trial's `backtest_round1.log`.
- Used PEPPER rows only (`INTARIAN_PEPPER_ROOT`).
- Bucket PnL computed from bucket-end PnL deltas; table reports mean bucket PnL across days.

## PEPPER total/day summary
| trial   |   total_pnl |   best_day |   worst_day |   day_std |   avg_day_max_dd |   worst_day_max_dd |   avg_step_std |   avg_positive_step_ratio |
|:--------|------------:|-----------:|------------:|----------:|-----------------:|-------------------:|---------------:|--------------------------:|
| trial33 |     130,558 |     45,310 |      41,013 |    1825.8 |           588769 |            634,900 |        26995.7 |                       0.4 |
| trial23 |     125,964 |     44,504 |      40,586 |    1783   |           590617 |            633,100 |        25636.1 |                       0.4 |

## Day ranking
| trial   |   day |   day_pnl |   day_rank |
|:--------|------:|----------:|-----------:|
| trial33 |    -2 |    45,310 |          1 |
| trial23 |    -2 |    44,504 |          2 |
| trial33 |    -1 |    44,235 |          1 |
| trial23 |    -1 |    40,874 |          2 |
| trial33 |     0 |    41,013 |          1 |
| trial23 |     0 |    40,586 |          2 |

## Per-day max drawdown (abs)
| trial   |   day |   day_max_dd |
|:--------|------:|-------------:|
| trial23 |    -2 |      549,450 |
| trial33 |    -2 |      549,450 |
| trial23 |    -1 |      589,300 |
| trial33 |    -1 |      581,956 |
| trial33 |     0 |      634,900 |
| trial23 |     0 |      633,100 |

## Intraday bucket PnL mean by trial (0 early -> 9 late)
| trial   |   0 |    1 |   2 |     3 |     4 |     5 |   6 |   7 |     8 |       9 |
|:--------|----:|-----:|----:|------:|------:|------:|----:|----:|------:|--------:|
| trial23 | 170 | 88.5 | 304 | 675.5 | 296.5 | 500.5 | 322 | 413 | 490.5 | 40901.2 |
| trial33 | 170 | 78   | 301 | 668   | 293.5 | 486.5 | 316 | 408 | 483   | 42451.3 |

## Bucket delta (trial33 - trial23)
|   bucket |   trial33_bucket_pnl |   trial23_bucket_pnl |   delta_33_minus_23 |
|---------:|---------------------:|---------------------:|--------------------:|
|        0 |                170   |                170   |                 0   |
|        1 |                 78   |                 88.5 |               -10.5 |
|        2 |                301   |                304   |                -3   |
|        3 |                668   |                675.5 |                -7.5 |
|        4 |                293.5 |                296.5 |                -3   |
|        5 |                486.5 |                500.5 |               -14   |
|        6 |                316   |                322   |                -6   |
|        7 |                408   |                413   |                -5   |
|        8 |                483   |                490.5 |                -7.5 |
|        9 |              42451.3 |              40901.2 |              1550.2 |
