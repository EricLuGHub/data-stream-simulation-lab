# R2 Trial 2 Report: PEPPER MAF-Aware Variant

## Why this trial exists

The round description says a Market Access Fee can buy access to an additional 25% of quotes for the top half of bidders. The local Prosperity 4 backtester does not expose that fee as a callable strategy input, so the practical way to respond is to make the strategy MAF-aware in behavior rather than in API usage.

This trial does that by splitting the logic into a core quoting layer and a bonus layer. The bonus layer is only activated when the signal quality is strong enough to justify paying for extra quote access in a real submission.

## Algorithm notes

The strategy is still PEPPER-only and keeps the same basic structure as the previous high-risk trial:

- best bid / best ask / mid extraction
- wall-mid estimation from heavy book levels
- EMA and drift anchoring
- residual z-score on mid vs fair value
- inventory-aware target sizing by time bucket
- carry floor late in the session

The MAF-aware changes are:

- a confidence score built from slope, z-score, participation, and time progression
- a `maf_bonus` multiplier of `1.25` when confidence is high enough
- extra taking capacity only when the bonus layer is active
- slightly tighter quoting when confidence is very high
- a stricter suppression of weak buy orders when the bonus layer is not justified

In plain terms, the strategy behaves as if it would only pay for extra quote access when it already has a strong directional edge.

## Backtest result

Full round 2 backtest:

- Day -1: `49,276`
- Day 0: `49,635`
- Day 1: `49,768`
- Total: `148,680`

Risk metrics from the full stitched run:

- Sharpe: `194.5745`
- Annualized Sharpe: `3,088.7739`
- Sortino: `inf`
- Max drawdown abs: `678,000`
- Max drawdown pct: `557.9089`
- Calmar: `0.2193`

The full log is saved at [full_round2_backtest.log](full_round2_backtest.log).

## Comparison to the prior high-risk trial

The earlier high-risk tuned trial had a full round 2 total of `148,256`. This MAF-aware variant improves that to `148,680`, a gain of `424`.

Day-level comparison:

- Day -1: `49,455` -> `49,276`
- Day 0: `49,680` -> `49,635`
- Day 1: `49,121` -> `49,768`

Interpretation:

- The MAF-aware version gives up a little on the training days.
- It picks up more on the holdout day 1.
- The extra quote layer looks directionally useful, but the gain is small enough that this is a refinement, not a structural breakthrough.

## Observations

1. The MAF rule does not change the simulator interface in this repo, so there is no direct fee-payment mechanism to test.
2. The best practical response is to use the extra-quote concept only when confidence is already high.
3. The result stayed profitable on all three days, so the added aggressiveness did not destabilize the strategy.
4. The drawdown numbers remain very large, so the strategy is still aggressive and should not be treated as low-risk.

## Bottom line

If the real contest environment actually awards extra quote access for paying MAF, this variant is the right style of response: only spend that access when the signal is strong.

For the local backtester, the change is still just a strategy refinement, not a simulator feature. It modestly improves total PnL versus the previous high-risk trial, but the edge is small.

4368