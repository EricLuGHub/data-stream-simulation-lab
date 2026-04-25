# Round 3 Reverse Engineering Report

## Summary

The strongest mechanism found is not a recoverable public RNG seed for the underlying price paths. `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT` have discrete random-walk-like increments with mild negative first-lag autocorrelation, but observable-state forecasts barely beat a no-change baseline on held-out day 2.

The exploitable mechanism is the `VEV_*` voucher ladder. The vouchers are generated from a Black-Scholes-like call option formula on `VELVETFRUIT_EXTRACT`, with a strike-dependent implied volatility smile. Fitting the chain on days 0 and 1 predicts voucher mid prices on day 2 well enough to trade residual mispricings.

## Evidence

- Price rows: 360,000 across days 0, 1, 2.
- Products: `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, and `VEV_4000` through `VEV_6500`.
- Underlying one-tick forecast on held-out day 2:
  - `VELVETFRUIT_EXTRACT` horizon 1 MAE: `0.8631` vs no-change baseline `0.8641`.
  - `HYDROGEL_PACK` horizon 1 MAE: `1.6147` vs no-change baseline `1.6656`.
- Best global voucher Black-Scholes fit on days 0 and 1:
  - `tau_scale=290`
  - `sigma=0.225`
  - RMSE `1.2534`
  - MAE `0.8074`

Per-strike fitted volatility:

| Product | Sigma | Train RMSE |
| --- | ---: | ---: |
| `VEV_4000` | 0.495 | 0.828 |
| `VEV_4500` | 0.285 | 0.761 |
| `VEV_5000` | 0.225 | 0.758 |
| `VEV_5100` | 0.225 | 1.308 |
| `VEV_5200` | 0.225 | 1.641 |
| `VEV_5300` | 0.225 | 1.567 |
| `VEV_5400` | 0.210 | 1.673 |
| `VEV_5500` | 0.230 | 0.688 |
| `VEV_6000` | 0.345 | 0.175 |
| `VEV_6500` | 0.520 | 0.179 |

`VEV_5500` was excluded from the submitted strategy despite fitting well because its public-fill economics were negative in backtests.

## Trader

Implemented in `codex_research/r3_option_smile_trader.py`.

Behavior:

- Observe current `VELVETFRUIT_EXTRACT` best bid/ask midpoint.
- Infer option time-to-expiry from day/timestamp.
- Price each active voucher using the fitted Black-Scholes smile.
- Cross the spread when the best quote is mispriced versus model fair value.
- Post inside the spread when model fair value is comfortably inside the market.
- Do not hedge with `VELVETFRUIT_EXTRACT`; tested delta hedging reduced PnL because spread cost dominated.

## Backtest PnL

Command:

```bash
.venv/bin/prosperity4btest cli codex_research/r3_option_smile_trader.py 3 --data codex_research/backtest_data --no-progress --out codex_research/r3_option_smile_backtest.log
```

Result:

| Day | PnL |
| --- | ---: |
| Round 3 day 0 | 1,910 |
| Round 3 day 1 | 11,365 |
| Round 3 day 2 | 16,653 |
| Total | 29,928 |

Risk metrics:

- Final PnL: `29,928`
- Sharpe: `1.3357`
- Annualized Sharpe: `21.2028`
- Max drawdown: `49,458`

## Conclusion

I did not find evidence that the public order book reveals enough state to recover the hidden seed and perfectly forecast future underlying order flow. The reverse-engineered, tradeable generator is the voucher pricing formula: the `VEV_*` products are option values derived from `VELVETFRUIT_EXTRACT`, with a stable implied-volatility smile.

The resulting trader does not perfectly predict every future price, but it predicts the voucher fair values accurately enough to produce positive PnL on every available day and the strongest PnL on the held-out day 2.
