# Round 1 Results Summary

**Total PnL: 52,331.86**

| Product | PnL | Strategy | Price Action |
|---------|-----|----------|-------------|
| ASH_COATED_OSMIUM | 10,891.61 | Market-making | Mean-reverting ~10,000 |
| INTARIAN_PEPPER_ROOT | 41,440.25 | Trend-following + MM | Linear uptrend 13,000 -> 14,000 |

---

## ASH_COATED_OSMIUM

- Price stayed flat around 10,000 the entire day
- Market-making captured avg spread of 6.64 across 3,284 units of turnover
- Position stayed well-bounded (oscillated between -18 and +33)
- PnL grew steadily with no major drawdowns
- **Verdict: Performed well. No major issues.**

## INTARIAN_PEPPER_ROOT

- Price followed a near-perfect linear uptrend: 13,000 -> 14,000 (+1,000 points)
- Algo was mostly near max position (45-50) from t=50,000 onward
- **Theoretical optimal (buy 50, hold): ~50,000 PnL**
- **Actual: 41,440 PnL (shortfall of ~8,560)**

### What went wrong

1. **Declining `base_target` (44 -> 18)**: The algo reduces target position over time via `base_target = 44 + (18-44) * progress`. This is counterproductive for a trending product -- the later you hold, the more each unit gains. By end-of-day, target was ~18-24, actively shedding position.

2. **Excessive selling into the uptrend**: 1,059 units sold total during a continuous uptrend. Sell orders kept posting because `sell_qty = min(sell_cap, max(1, int(18 * (1 + inv_ratio))))` is always nonzero, and `suppress_sell` only triggers when `pos < target - 2`.

3. **Position collapse at t=100,000 (pos dropped to 15)**: Trend detection lagged (needs 8 ticks of history), and z-score likely triggered selling before trend was confirmed.

4. **Early sells were the most costly**: Selling 67 units before t=100,000 at avg ~13,081 cost ~61,568 in opportunity. Selling 125 units in t=100k-200k at avg ~13,166 cost another ~104,288. Earlier selling hurts more with a linear trend.

### Sell activity breakdown

| Time Window | Units Sold | Avg Price | Missed Gain |
|-------------|-----------|-----------|-------------|
| 0 - 100k | 67 | 13,081 | 61,568 |
| 100k - 200k | 125 | 13,166 | 104,288 |
| 200k - 300k | 103 | 13,253 | 76,984 |
| 300k - 400k | 99 | 13,343 | 65,043 |
| 400k - 500k | 118 | 13,447 | 65,294 |
| 500k - 600k | 99 | 13,553 | 44,286 |
| 600k - 700k | 108 | 13,645 | 38,293 |
| 700k - 800k | 106 | 13,746 | 26,918 |
| 800k - 900k | 140 | 13,845 | 21,740 |
| 900k - 1M | 94 | 13,944 | 5,249 |

---

## Recommendations for next round

- **PEPPER target should not decline over time** -- if trend is detected, hold max position
- **Suppress sells more aggressively** when trend > 0 (current condition `pos < target - 2` is too narrow)
- **Reduce `sell_qty` base** from 18 to near 0 when trend is positive
- **Add a momentum signal** (e.g., price change rate) that can override the declining target
- **Faster trend detection** -- 8-tick lookback is too slow; consider starting with a prior/assumption
- **ASH is fine** -- keep the market-making logic as-is
