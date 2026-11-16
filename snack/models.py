from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class Office(Enum):
    OSLO = "oslo"
    BENGALURU = "bengaluru"


# office -> (monthly budget, currency)
BUDGETS = {
    Office.OSLO: (Decimal("6000"), "NOK"),
    Office.BENGALURU: (Decimal("15000"), "INR"),
}


class RefillState(Enum):
    EMPTY = "empty"            # reported; waiting for a volunteer to commit
    CLAIMED = "claimed"        # exactly one volunteer committed to buy
    PURCHASED = "purchased"    # receipt received
    SUBMITTED = "submitted"    # reimbursement claim filed with HR
    REIMBURSED = "reimbursed"  # HR approved and paid


@dataclass
class Volunteer:
    id: str
    name: str
    office: Office                       # home office
    payroll_currency: str
    available: bool = True               # at a desk and reachable today
    visiting: Optional[Office] = None    # temporarily working from the other office
    last_purchase_at: Optional[datetime] = None

    @property
    def present_office(self) -> Office:
        return self.visiting or self.office


@dataclass
class Purchase:
    buyer_id: str
    office: Office
    amount: Decimal
    currency: str
    description: str
    receipt_image: str
    purchased_at: datetime


@dataclass
class Refill:
    id: str
    office: Office
    created_at: datetime
    state: RefillState = RefillState.EMPTY
    assignee_id: Optional[str] = None          # volunteer currently asked or committed
    asked_at: Optional[datetime] = None        # when the current candidate was asked
    claimed_at: Optional[datetime] = None
    asked: list = field(default_factory=list)  # volunteer ids already asked for this refill
    purchase: Optional[Purchase] = None
    hr_claim_id: Optional[str] = None
