# Snack Counter Automation — Design

## What "automate" means here

The snacks, the shopping and the receipts stay human. What the system automates is
**coordination**: deciding *who* refills, making sure *exactly one* person does,
chasing stalled refills, filing the reimbursement claim the moment the receipt
exists, and keeping the books. Everything happens through the company chat tool,
because every employee already has it — no new app to install.

## Refill lifecycle: from "empty" to "reimbursed"
  
```
EMPTY ──accept──▶ CLAIMED ──receipt──▶ PURCHASED ──auto──▶ SUBMITTED ──HR approves──▶ REIMBURSED
  ▲                  │
  └───── timeout ────┘   (claim abandoned → back to EMPTY, next volunteer asked)
```

1. **EMPTY** — anyone reports the box empty in chat (one message / button press).
   Duplicate reports attach to the existing refill; there is never more than one
   active refill per box.
2. The system picks the best candidate — the *available* volunteer at that office
   who bought **least recently** — and asks them directly in chat, including the
   remaining monthly budget ("spend at most X"). If they don't respond within a
   few hours, the next candidate is asked.
3. **CLAIMED** — a volunteer commits. The claim is atomic: the second person to
   tap "I'll do it" is told someone already has it. This is the double-buy fix.
4. If a claimer goes silent for 24h (got sick, went home), the claim times out,
   returns to EMPTY, and the next candidate is asked. The silent claimer is
   skipped for this refill. This is the "box empty for days" fix.
5. **PURCHASED → SUBMITTED** — the volunteer posts the receipt photo + amount in
   chat. The system immediately files the claim with the HR API (amount,
   currency, description, receipt image, employee ID) and records the purchase
   in the ledger. The volunteer never touches the HR system and never waits on a
   human to forward their receipt — the only remaining delay is HR's own 1–10
   day approval, which is outside our control.
6. **REIMBURSED** — HR approves; the system notifies the volunteer. Claims
   pending unusually long can be nudged.

## Parts and the data each keeps

| Part | Keeps |
|---|---|
| **Refill tracker** | refill tasks: state, office, who was asked, who claimed, timestamps, HR claim id |
| **Volunteer roster** | per volunteer: home office, current office (visits!), availability (office / home / holiday), payroll currency, when they last bought |
| **Budget ledger** | every purchase: office, amount, currency, description, date. Derives monthly totals, remaining budget, the management report |
| **Chat adapter** | nothing — translates chat messages to/from the core (simulated here) |
| **HR adapter** | nothing — wraps the HR claims API (simulated here) |

Core logic is pure and takes an injected clock, so every timing rule is testable
without sleeping.

## Problem → mechanism

| Problem today | Mechanism |
|---|---|
| Box empty for days, "someone else will do it" | A *specific* person is asked, with a response timeout and automatic hand-off |
| Two people buy the same day | One active refill per box + atomic claim; second claimer rejected |
| Few people do most refills | Candidate = least-recently-purchased available volunteer; load rotates by construction |
| Weeks waiting for money | Claim auto-filed the instant the receipt is posted; status tracked and nudged |
| Nobody knows monthly spend | Ledger + one monthly report covering both offices |
| Which snacks get eaten | Purchase descriptions give a crude signal (see non-goals) |

## Rules and edge cases

- **Budget**: each claim message shows the remaining monthly budget. If a receipt
  still takes the office over budget, the claim is **filed anyway** — the
  volunteer already paid and must be made whole — but the overrun is flagged to
  the admin and in the report. Prevention is soft (warnings), not a hard block.
- **Currencies**: a purchase is in the office's currency (visiting Oslo employee
  refilling in Bengaluru pays INR → claim filed in INR). Payroll-currency
  conversion is the HR system's job, as stated. The monthly report shows each
  office in its own currency side by side; we deliberately do **not** invent an
  FX rate to produce one blended number — if management insists, a rate source
  becomes a (small) feature.
- **Availability**: volunteers toggle themselves (office / home / holiday) in
  chat; only people physically at the office are candidates. Visitors count at
  the office they're visiting.

## Trade-offs and non-goals

- **In-memory state, single-threaded core.** The claim check-and-set is atomic
  because the core is single-threaded; in production this becomes one
  `UPDATE … WHERE state='EMPTY'` on Postgres. The interesting logic is identical.
- **Not built — real chat/HR integrations.** Adapters are faked; the seams are
  where real webhooks would plug in.
- **Not built — inventory / per-snack tracking.** Would need barcode scanning or
  manual itemization; cost exceeds value for a snack box. Purchase descriptions
  are enough for a rough "what do we buy" signal.
- **Not built — receipt OCR / amount validation.** Volunteer types the amount;
  HR approval is already the human check on the receipt.
- **Not built — hard budget enforcement.** Blocking a refill punishes the whole
  office for a spreadsheet rule; warnings + the monthly report give management
  the control they actually asked for.

## Open questions sent to the reviewers (assumptions used meanwhile)

1. Combined report: one currency or per-office? → *Assumed per-office, no FX.*
2. Over budget: block or warn? → *Assumed warn + flag, never refuse reimbursement.*
3. Who may report an empty box? → *Assumed anyone, deduplicated.*
4. Visitor buys at the other office — claim in purchase currency, payroll
   conversion by HR? → *Assumed yes, per the brief.*
