# Trial 26: Merged Trial 14 ASH + Trial 23 PEPPER

Composition:
- ASH logic copied from `R1/trial14/125405.py`
- PEPPER logic copied from `R1/trial23/126201.py`
- Combined into one `Trader` class with separate product handlers.

Backtest command:
- `./.venv/bin/prosperity4btest R1/trial26/126301.py 1 --out R1/trial26/backtest_round1.log --no-progress`

Round 1 backtest results:
- Day -2: ASH 9,089 + PEPPER 44,504 = 53,593
- Day -1: ASH 11,185 + PEPPER 40,874 = 52,059
- Day 0: ASH 10,029 + PEPPER 40,586 = 50,615
- Total: 156,267

Confirmation notes:
- PEPPER performance is preserved exactly vs trial23 (44,504 / 40,874 / 40,586).
- ASH contribution is positive and materially boosts total PnL.
- Merged strategy is successfully runnable and logged at `R1/trial26/backtest_round1.log`.
