"""Simulates one month of snack life across both offices. Run: python3 demo.py"""
from datetime import datetime, timedelta
from decimal import Decimal

from snack.fakes import FakeChat, FakeHR
from snack.lifecycle import SnackService
from snack.models import Office, Volunteer


class Clock:
    def __init__(self, start):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, **kwargs):
        self.t += timedelta(**kwargs)


clock = Clock(datetime(2026, 11, 2, 9, 0))
chat, hr = FakeChat(), FakeHR()
service = SnackService(
    [
        Volunteer("alice", "Alice", Office.OSLO, "NOK"),
        Volunteer("bjorn", "Bjørn", Office.OSLO, "NOK"),
        Volunteer("carl", "Carl", Office.OSLO, "NOK", available=False),  # holiday
        Volunteer("divya", "Divya", Office.BENGALURU, "INR"),
        Volunteer("esha", "Esha", Office.BENGALURU, "INR"),
        Volunteer("viggo", "Viggo", Office.OSLO, "NOK", visiting=Office.BENGALURU),
    ],
    chat,
    hr,
    now=clock,
)

purchases = [
    (Office.OSLO, Decimal("850"), "coffee, fruit, chocolate"),
    (Office.BENGALURU, Decimal("2400"), "biscuits, namkeen, tea"),
    (Office.OSLO, Decimal("1150"), "nuts, crispbread"),
    (Office.BENGALURU, Decimal("1800"), "fruit, chips"),
    (Office.OSLO, Decimal("600"), "tea, biscuits"),
]

for office, amount, items in purchases:
    refill = service.report_empty(office)
    buyer = refill.assignee_id
    print(f"[{clock().date()}] {office.value}: empty. Asked {buyer}.")
    service.claim(refill.id, buyer)
    clock.advance(hours=3)
    service.submit_receipt(refill.id, buyer, amount, items, "receipt.jpg")
    print(f"             {buyer} bought for {amount}, claim {refill.hr_claim_id} filed.")
    clock.advance(days=4)

# demonstrate an abandoned claim being handed off
refill = service.report_empty(Office.OSLO)
ghost = refill.assignee_id
service.claim(refill.id, ghost)
print(f"[{clock().date()}] oslo: empty. {ghost} claimed... then went silent.")
clock.advance(hours=25)
service.check_timeouts()
print(f"             claim timed out -> handed to {refill.assignee_id}.")
service.claim(refill.id, refill.assignee_id)
service.submit_receipt(refill.id, refill.assignee_id, Decimal("900"), "mixed snacks", "r.jpg")

for claim_id in list(hr.claims):
    hr.approve(claim_id)

print("\n--- Monthly report, November 2026 ---")
for office, row in service.ledger.monthly_report(2026, 11).items():
    flag = "  ** OVER BUDGET **" if row["over_budget"] else ""
    print(f"{office}: {row['total']} {row['currency']} of {row['budget']} budget{flag}")
    for line in row["purchases"]:
        print(f"   {line}")

print(f"\n{len(chat.sent)} chat messages sent, {len(hr.claims)} HR claims, all approved.")
