# Round 1 Backtest Report (Trials 1 to 5, All Available Days)

## Scope
- Backtester: `prosperity4btest`
- Algorithms tested:
  - `R1/trial1/121301.py`
  - `R1/trial2/121951.py`
  - `R1/trial3/122408.py`
  - `R1/trial4/123161.py`
  - `R1/trial5/123629.py`
- Days run for Round 1: `-2`, `-1`, `0`
- Command pattern used:
  - `prosperity4btest <trial_file> 1-<day> --no-out`

## Note on Day Labels
Requested days were `0, 1, 2`, but the installed backtester has Round 1 data for `-2, -1, 0`.
This report covers all available Round 1 days.

## Results by Trial and Day

| Trial | Day | ASH_COATED_OSMIUM | INTARIAN_PEPPER_ROOT | Total profit |
|---|---:|---:|---:|---:|
| 1 | -2 | 4,844 | 48,438 | 53,283 |
| 1 | -1 | 5,868 | 48,603 | 54,471 |
| 1 | 0 | 5,263 | 48,734 | 53,997 |
| 2 | -2 | 4,106 | 22,013 | 26,118 |
| 2 | -1 | 4,489 | 18,063 | 22,552 |
| 2 | 0 | 4,890 | 19,922 | 24,812 |
| 3 | -2 | 5,844 | 27,287 | 33,132 |
| 3 | -1 | 6,102 | 21,601 | 27,703 |
| 3 | 0 | 6,562 | 23,672 | 30,234 |
| 4 | -2 | 5,489 | 35,317 | 40,806 |
| 4 | -1 | 5,726 | 34,700 | 40,426 |
| 4 | 0 | 5,752 | 35,086 | 40,838 |
| 5 | -2 | 5,489 | 33,333 | 38,822 |
| 5 | -1 | 5,726 | 34,810 | 40,536 |
| 5 | 0 | 5,752 | 34,986 | 40,738 |

## Aggregate Summary by Trial (Across 3 Days)

| Trial | ASH Sum | PEPPER Sum | Total Sum | Average per Day |
|---|---:|---:|---:|---:|
| 1 | 15,975 | 145,775 | 161,750 | 53,916.67 |
| 2 | 13,485 | 59,998 | 73,482 | 24,494.00 |
| 3 | 18,508 | 72,560 | 91,069 | 30,356.33 |
| 4 | 16,967 | 105,103 | 122,070 | 40,690.00 |
| 5 | 16,967 | 103,129 | 120,096 | 40,032.00 |

## Rankings

### Best Trial by Total Across All Days
1. Trial 1: 161,750
2. Trial 4: 122,070
3. Trial 5: 120,096
4. Trial 3: 91,069
5. Trial 2: 73,482

### Best Single Trial-Day Run
1. Trial 1, Day -1: 54,471
2. Trial 1, Day 0: 53,997
3. Trial 1, Day -2: 53,283
4. Trial 4, Day 0: 40,838
5. Trial 4, Day -2: 40,806

## Observations
- Trial 1 is consistently dominant on every available day.
- ASH contribution is relatively stable across trials; most total-performance gap is driven by INTARIAN_PEPPER_ROOT.
- Trials 4 and 5 are close, with Trial 4 slightly stronger overall.
