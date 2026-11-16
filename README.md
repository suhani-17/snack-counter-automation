# Snack Counter Automation

Automates the *coordination* of snack refills for the Oslo and Bengaluru
offices: who buys, exactly one buyer per refill, hand-off when someone stalls,
instant reimbursement filing, and one monthly spend report. Design and
trade-offs: **[DESIGN.md](DESIGN.md)**.

## Run it

Requires Python 3.10+. Tests need `pytest` (`pip install pytest`); everything
else is standard library.

```bash
python3 -m pytest        # 23 tests covering the rules below
python3 demo.py          # simulates a month across both offices
```

## Layout

```
snack/
  models.py      # offices, budgets, volunteers, refill state machine, purchases
  assignment.py  # who buys: least-recently-purchased available volunteer
  budget.py      # ledger, monthly totals, remaining budget, management report
  lifecycle.py   # SnackService: claims, timeouts, receipt -> HR claim
  fakes.py       # simulated chat tool and HR system
tests/           # one file per rule group
demo.py          # end-to-end simulation with printed monthly report
```

## The rules the tests prove

- **Two people cannot commit to the same refill** — second `claim()` raises
  (`tests/test_claiming.py`).
- **A refill nobody completes is handed to someone else** — ask-timeout skips
  silent candidates, claim-timeout reassigns abandoned claims
  (`tests/test_handoff.py`).
- **Budgets and totals are correct across both currencies** — Decimal money,
  NOK and INR never mixed, over-budget flagged (`tests/test_budget.py`).
- **Full lifecycle and the edge cases** — empty → reimbursed, visitor buying
  in the other office claims in the purchase currency, over-budget purchases
  are still reimbursed but flagged (`tests/test_lifecycle.py`).

## Key assumptions

Sent as questions to the reviewers; used these defaults meanwhile
(details in DESIGN.md):

1. Monthly report shows each office in its own currency — no invented FX rate.
2. Over budget warns and flags; a volunteer who already paid is always reimbursed.
3. Anyone can report an empty box; duplicates attach to the active refill.
4. A visitor's claim is filed in the purchase currency; payroll-currency
   conversion is the HR system's job (as stated in the brief).
