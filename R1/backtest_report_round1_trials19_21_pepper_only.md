# Round 1 Backtest Report (Trials 19 to 21, PEPPER-only)

Scope:
- Product focus: `INTARIAN_PEPPER_ROOT` only
- Backtester: `./.venv/bin/prosperity4btest`
- Command style:
  - `./.venv/bin/prosperity4btest R1/trialN/<file>.py 1 --out R1/trialN/backtest_round1.log --no-progress`

## Strategy Snapshot

| Trial | File | Core idea |
| --- | --- | --- |
| trial19 | `R1/trial19/126001.py` | Pullback-to-trend re-entry using residual z-score and long bias |
| trial20 | `R1/trial20/126002.py` | Momentum continuation with fast/slow EMA regime and trailing de-risk |
| trial21 | `R1/trial21/126003.py` | Hybrid trend-anchor + residual z-gated entries |

## Performance Summary

| Trial | Day -2 | Day -1 | Day 0 | Total PnL | Sharpe | Max Drawdown Abs | Calmar |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| trial20 | 27340 | 29989 | 30800 | 88128 | 16.2316 | 542156 | 0.1626 |
| trial21 | 29796 | 28982 | 27831 | 86610 | 29.2341 | 760315 | 0.1139 |
| trial19 | 31595 | 23300 | 23776 | 78671 | 5.6301 | 1026465 | 0.0766 |

## Ranking and Takeaways

1. `trial20` has the best total PnL and strongest drawdown efficiency among the three.
2. `trial21` is close in total PnL and appears very stable day-to-day, but with higher drawdown than `trial20`.
3. `trial19` is profitable and aligns with pullback thesis, but currently over-aggressive in shock entries, producing the largest drawdown.

## Recommendation

- Use `trial20` as the new PEPPER baseline for next iteration.
- Keep `trial21` as secondary candidate for robustness checks.
- Retune `trial19` entry sizing before promoting it.
