# Trial 5 vs Successful PEPPER Trials

This note compares Trial 5 against the PEPPER trials that actually held up in local round-1 backtests and were worth keeping as reference points.

## Local Round-1 PEPPER Comparison

| Trial | Type | PEPPER total | Delta vs Trial 5 | Notes |
| --- | --- | ---: | ---: | --- |
| Trial 5 | Baseline / mixed-product submission anchor | 103,129 | 0 | Submission-proven anchor, but the local PEPPER backtest is the weakest in this set. |
| Trial 23 | PEPPER-only | 125,964 | +22,835 | Wall-mid trend gating; strong step up from Trial 5. |
| Trial 30 | PEPPER-only | 116,283 | +13,154 | Time-profiled carry + pullback entries; better than Trial 5, but below the best PEPPER-only variants. |
| Trial 32 | PEPPER-only | 125,203 | +22,074 | Participation-adaptive carry; very close to Trial 23. |
| Trial 33 | PEPPER-only | 130,558 | +27,429 | Best pure PEPPER local result before the submission-focused variants. |
| Trial 37 | PEPPER-only | 145,457 | +42,328 | Strongest local PEPPER total, but later submission results showed it was brittle. |
| Trial 38 | PEPPER-only | 144,150 | +41,021 | Slightly below Trial 37 locally, but designed to be more robust in weak/choppy late regimes. |

## Merged Run

| Trial | Type | Total local PnL | PEPPER component | Notes |
| --- | --- | ---: | ---: | --- |
| Trial 34 | ASH + PEPPER merge | 160,861 | 130,558 | Uses Trial 14-style ASH logic plus Trial 33 PEPPER logic. Total is not directly comparable to PEPPER-only trials, but the PEPPER side is the same as Trial 33. |

## Takeaway

Trial 5 is the safest submission anchor because it already proved itself on submission, but locally it is clearly behind the later PEPPER work. Among the PEPPER-only variants, Trial 33 is the best stable improvement over Trial 5, with Trials 37 and 38 pushing farther locally at the cost of higher submission risk. Trial 34 is the best overall local total, but that is mostly because it combines ASH and PEPPER rather than improving PEPPER alone.

## Backtest Source

- Trial 5 local backtest: [R1/trial5/backtest_round1.log](../../trial5/backtest_round1.log)
- Trial 23 summary: [R1/trial23/summary.md](../../trial23/summary.md)
- Trial 30 summary: [R1/trial30/summary.md](../../trial30/summary.md)
- Trial 32 summary: [R1/trial32/summary.md](../../trial32/summary.md)
- Trial 33 summary: [R1/trial33/summary.md](../../trial33/summary.md)
- Trial 34 summary: [R1/trial34/summary.md](../../trial34/summary.md)
- Trial 37 summary: [R1/trial37/summary.md](../../trial37/summary.md)
- Trial 38 local backtest: generated from [R1/trial38/backtest_round1.log](../../trial38/backtest_round1.log)
