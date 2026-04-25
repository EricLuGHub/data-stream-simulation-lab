# Round 3 Reverse Engineering Journal

## Data inventory

- Price rows: 360,000; trade rows: 4,048.
- Products: HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_4000, VEV_4500, VEV_5000, VEV_5100, VEV_5200, VEV_5300, VEV_5400, VEV_5500, VEV_6000, VEV_6500.
- Timestamps are 0..999900 in 100ms increments, with one row per product per timestamp per day.

## Deterministic price path tests

| product             |   day |    n |   zero_frac |   mean_delta |   std_delta |   unique_deltas | top_deltas                                                              |   lag1_delta_corr |   lag2_delta_corr |
|:--------------------|------:|-----:|------------:|-------------:|------------:|----------------:|:------------------------------------------------------------------------|------------------:|------------------:|
| HYDROGEL_PACK       |     0 | 9999 |    0.186119 |  -0.00420042 |     2.19122 |              39 | 0:1861, -1:1565, 1:1507, 2:1123, -2:1070, -3:583, 3:581, -4:248         |         -0.13786  |       -0.00853047 |
| HYDROGEL_PACK       |     1 | 9999 |    0.173617 |   0.00570057 |     2.14832 |              43 | 0:1736, 1:1600, -1:1563, 2:1095, -2:1083, 3:544, -3:542, 4:229          |         -0.12399  |        0.0113308  |
| HYDROGEL_PACK       |     2 | 9999 |    0.180818 |  -0.00010001 |     2.16993 |              34 | 0:1808, -1:1592, 1:1521, 2:1063, -2:1059, 3:580, -3:531, -4:265         |         -0.125352 |        0.0214817  |
| VELVETFRUIT_EXTRACT |     0 | 9999 |    0.249825 |  -0.00060006 |     1.12058 |              22 | 0:2498, 1:1602, -1:1553, 0.5:1087, -0.5:1072, 1.5:483, -1.5:478, -2:425 |         -0.150977 |        0.0155734  |
| VELVETFRUIT_EXTRACT |     1 | 9999 |    0.244324 |   0.00205021 |     1.13487 |              19 | 0:2443, 1:1647, -1:1535, 0.5:1107, -0.5:1047, -1.5:467, 1.5:456, -2:450 |         -0.16929  |       -0.00274164 |
| VELVETFRUIT_EXTRACT |     2 | 9999 |    0.245925 |   0.00280028 |     1.13811 |              20 | 0:2459, 1:1570, -1:1531, -0.5:1105, 0.5:1044, -1.5:473, 1.5:468, 2:466  |         -0.155148 |        0.00223288 |

The raw underlying deltas are small and discrete, but day-to-day paths do not line up as a reused seed/phase. A simple observable-state regression has only moderate directional skill, which argues against an easily recoverable next-random-number stream from the public book alone.

## Observable forecast diagnostics on held-out day 2

| product             |   horizon_ticks |    mae |   actual_abs_mae_baseline |   corr |   direction_accuracy |   signal_std |
|:--------------------|----------------:|-------:|--------------------------:|-------:|---------------------:|-------------:|
| HYDROGEL_PACK       |               1 | 1.6147 |                    1.6656 | 0.3048 |               0.4317 |       0.6496 |
| HYDROGEL_PACK       |               2 | 2.2216 |                    2.2555 | 0.2167 |               0.4648 |       0.6562 |
| HYDROGEL_PACK       |               5 | 3.4497 |                    3.4737 | 0.1523 |               0.4881 |       0.7042 |
| HYDROGEL_PACK       |              10 | 4.8102 |                    4.8531 | 0.1434 |               0.5117 |       0.9051 |
| HYDROGEL_PACK       |              20 | 6.7207 |                    6.8144 | 0.1676 |               0.5301 |       1.4088 |
| HYDROGEL_PACK       |              50 | 9.9904 |                   10.2274 | 0.2552 |               0.5507 |       3.1439 |
| VELVETFRUIT_EXTRACT |               1 | 0.8631 |                    0.8641 | 0.3007 |               0.4556 |       0.3469 |
| VELVETFRUIT_EXTRACT |               2 | 1.1438 |                    1.1452 | 0.2320 |               0.4669 |       0.3564 |
| VELVETFRUIT_EXTRACT |               5 | 1.7333 |                    1.7359 | 0.1525 |               0.4819 |       0.4054 |
| VELVETFRUIT_EXTRACT |              10 | 2.4020 |                    2.3995 | 0.1149 |               0.4884 |       0.5566 |
| VELVETFRUIT_EXTRACT |              20 | 3.3494 |                    3.3304 | 0.0986 |               0.4962 |       0.9697 |
| VELVETFRUIT_EXTRACT |              50 | 5.0363 |                    4.9818 | 0.1615 |               0.5131 |       2.2022 |

## Voucher mechanism

- Best single Black-Scholes grid fit on days 0-1: tau_scale=290.00, sigma=0.2250, RMSE=1.2534, MAE=0.8074.
- Per-strike implied volatility fit:

| product   |    strike |   sigma |   rmse |    mae |    bias |
|:----------|----------:|--------:|-------:|-------:|--------:|
| VEV_4000  | 4000.0000 |  0.4950 | 0.8278 | 0.2595 | -0.0030 |
| VEV_4500  | 4500.0000 |  0.2850 | 0.7606 | 0.4357 | -0.0028 |
| VEV_5000  | 5000.0000 |  0.2250 | 0.7580 | 0.5976 |  0.1625 |
| VEV_5100  | 5100.0000 |  0.2250 | 1.3077 | 1.0490 |  0.3562 |
| VEV_5200  | 5200.0000 |  0.2250 | 1.6410 | 1.4005 |  0.3338 |
| VEV_5300  | 5300.0000 |  0.2250 | 1.5674 | 1.3648 | -0.0613 |
| VEV_5400  | 5400.0000 |  0.2100 | 1.6726 | 1.3975 | -0.4565 |
| VEV_5500  | 5500.0000 |  0.2300 | 0.6884 | 0.5681 |  0.1057 |
| VEV_6000  | 6000.0000 |  0.3450 | 0.1750 | 0.1527 | -0.0478 |
| VEV_6500  | 6500.0000 |  0.5200 | 0.1790 | 0.1575 | -0.0695 |

The vouchers are not independent random walks. They are a formula-driven option chain on VELVETFRUIT_EXTRACT with a strike-dependent volatility smile. That gives a much stronger and more stable trading signal than trying to infer a hidden RNG seed for the underlying paths.
