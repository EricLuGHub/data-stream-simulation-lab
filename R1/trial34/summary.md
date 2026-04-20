# Trial 34: Merge of Trial14 ASH and Trial33 PEPPER

## Objective
Combine proven ASH passive inventory-disciplined logic with the new best PEPPER trial33 logic in one submission.

## Code
- ASH logic source: trial14 style model
- PEPPER logic source: trial33 model
- File: 126408.py
- Integration detail: namespaced `traderData` keys (`ash_*`, `pepper_*`) to avoid state-key collisions.

## Backtest (Round 1)
- Day -2: ASH 9,089 + PEPPER 45,310 = 54,399
- Day -1: ASH 11,185 + PEPPER 44,235 = 55,420
- Day 0: ASH 10,029 + PEPPER 41,013 = 51,042
- Total: 160,861

Risk metrics:
- Sharpe: 23.4097
- Max drawdown abs: 991,282
- Calmar: 0.1623

## Comparison
- Trial26 total: 156,267
- Trial34 total: 160,861
- Delta: +4,594

## Conclusion
This merged trial improves total local Round 1 PnL versus the prior merged baseline by preserving trial33 PEPPER gains while keeping ASH contribution stable.
