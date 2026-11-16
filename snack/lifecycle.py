"""The refill lifecycle: EMPTY -> CLAIMED -> PURCHASED -> SUBMITTED -> REIMBURSED,
with timeout hand-off back to EMPTY. See DESIGN.md."""
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import count
from typing import Iterable, Optional

from .assignment import pick_volunteer
from .budget import Ledger
from .models import BUDGETS, Office, Purchase, Refill, RefillState, Volunteer


class AlreadyClaimed(Exception):
    """A second volunteer tried to commit to a refill someone already has."""


class InvalidTransition(Exception):
    """Operation doesn't match the refill's current state or assignee."""


class SnackService:
    ASK_TIMEOUT = timedelta(hours=4)     # asked volunteer silent -> ask the next one
    CLAIM_TIMEOUT = timedelta(hours=24)  # committed but never bought -> hand off

    def __init__(self, volunteers: Iterable[Volunteer], chat, hr, now=datetime.now):
        self.volunteers = {v.id: v for v in volunteers}
        self.chat = chat
        self.hr = hr
        self.now = now
        self.ledger = Ledger()
        self.refills: dict[str, Refill] = {}
        self._seq = count(1)
        self.hr.on_approved = self._on_hr_approved

    # -- reporting an empty box ------------------------------------------------

    def report_empty(self, office: Office) -> Refill:
        """Anyone may report. Duplicate reports attach to the active refill,
        so there is never more than one refill in flight per box."""
        active = self._active_refill(office)
        if active:
            return active
        refill = Refill(
            id=f"refill-{next(self._seq)}", office=office, created_at=self.now()
        )
        self.refills[refill.id] = refill
        self._ask_next(refill)
        return refill

    def _active_refill(self, office: Office) -> Optional[Refill]:
        return next(
            (
                r
                for r in self.refills.values()
                if r.office is office
                and r.state in (RefillState.EMPTY, RefillState.CLAIMED)
            ),
            None,
        )

    def _ask_next(self, refill: Refill) -> None:
        candidate = pick_volunteer(
            self.volunteers.values(), refill.office, exclude=refill.asked
        )
        if candidate is None:
            refill.assignee_id = None
            refill.asked_at = None
            self.chat.send(
                f"#snacks-{refill.office.value}",
                f"Nobody available to refill the {refill.office.value} snack box "
                "— can anyone step in? (reply CLAIM)",
            )
            return
        refill.assignee_id = candidate.id
        refill.asked_at = self.now()
        refill.asked.append(candidate.id)
        budget, currency = BUDGETS[refill.office]
        remaining = self.ledger.remaining(refill.office, self.now())
        self.chat.send(
            candidate.id,
            f"The {refill.office.value} snack box is empty — can you refill it? "
            f"Budget left this month: {remaining} {currency}. Reply CLAIM.",
        )

    # -- claiming --------------------------------------------------------------

    def claim(self, refill_id: str, volunteer_id: str) -> Refill:
        refill = self.refills[refill_id]
        if refill.state is not RefillState.EMPTY:
            # ponytail: atomic because the core is single-threaded; in production
            # this is UPDATE refill SET state='claimed' WHERE id=? AND state='empty'
            raise AlreadyClaimed(
                f"{refill_id} already claimed by {refill.assignee_id}"
            )
        refill.state = RefillState.CLAIMED
        refill.assignee_id = volunteer_id
        refill.claimed_at = self.now()
        if volunteer_id not in refill.asked:
            refill.asked.append(volunteer_id)
        self.chat.send(
            volunteer_id,
            f"You're on it. Post the receipt photo and amount here when done "
            f"(within {int(self.CLAIM_TIMEOUT.total_seconds() // 3600)}h).",
        )
        return refill

    # -- receipt and reimbursement --------------------------------------------

    def submit_receipt(
        self,
        refill_id: str,
        volunteer_id: str,
        amount: Decimal,
        description: str,
        receipt_image: str,
    ) -> Refill:
        refill = self.refills[refill_id]
        if refill.state is not RefillState.CLAIMED or refill.assignee_id != volunteer_id:
            raise InvalidTransition(
                f"{refill_id} is {refill.state.value}, assignee {refill.assignee_id}"
            )
        _, currency = BUDGETS[refill.office]  # purchase is in the office's currency
        purchased_at = self.now()
        purchase = Purchase(
            buyer_id=volunteer_id,
            office=refill.office,
            amount=amount,
            currency=currency,
            description=description,
            receipt_image=receipt_image,
            purchased_at=purchased_at,
        )
        refill.purchase = purchase
        refill.state = RefillState.PURCHASED
        self.ledger.add(purchase)
        self.volunteers[volunteer_id].last_purchase_at = purchased_at

        if self.ledger.remaining(refill.office, purchased_at) < 0:
            self.chat.send(
                "#snacks-admin",
                f"{refill.office.value} is over its monthly snack budget "
                f"after a {amount} {currency} purchase.",
            )

        # File the claim immediately: the volunteer is paid in their payroll
        # currency by HR; currency conversion is HR's job.
        refill.hr_claim_id = self.hr.submit_claim(
            employee_id=volunteer_id,
            amount=amount,
            currency=currency,
            description=f"Snack refill, {refill.office.value}: {description}",
            receipt_image=receipt_image,
        )
        refill.state = RefillState.SUBMITTED
        self.chat.send(
            volunteer_id,
            f"Reimbursement claim {refill.hr_claim_id} filed for {amount} {currency}. "
            "HR approval takes 1-10 days; I'll ping you when it lands.",
        )
        return refill

    def _on_hr_approved(self, claim_id: str) -> None:
        refill = next(
            r for r in self.refills.values() if r.hr_claim_id == claim_id
        )
        refill.state = RefillState.REIMBURSED
        self.chat.send(
            refill.assignee_id,
            f"Claim {claim_id} approved — you'll be reimbursed with your next payroll.",
        )

    # -- timeouts (run periodically; tests call directly) ----------------------

    def check_timeouts(self) -> None:
        now = self.now()
        for refill in self.refills.values():
            if (
                refill.state is RefillState.EMPTY
                and refill.asked_at is not None
                and now - refill.asked_at >= self.ASK_TIMEOUT
            ):
                self._ask_next(refill)  # silent candidate: ask the next person
            elif (
                refill.state is RefillState.CLAIMED
                and now - refill.claimed_at >= self.CLAIM_TIMEOUT
            ):
                abandoner = refill.assignee_id
                refill.state = RefillState.EMPTY
                refill.assignee_id = None
                refill.claimed_at = None
                self.chat.send(
                    abandoner,
                    "No receipt in time — no worries, handing the refill to someone else.",
                )
                self._ask_next(refill)
