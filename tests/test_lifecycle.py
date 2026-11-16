from decimal import Decimal

from snack.models import Office, RefillState, Volunteer


def test_full_lifecycle_empty_to_reimbursed(service, chat, hr, clock):
    refill = service.report_empty(Office.OSLO)
    service.claim(refill.id, "alice")
    service.submit_receipt(
        refill.id, "alice", Decimal("850"), "coffee, fruit, chocolate", "receipt.jpg"
    )

    # Claim filed with HR immediately, with everything their API needs
    assert refill.state is RefillState.SUBMITTED
    claim = hr.claims[refill.hr_claim_id]
    assert claim["employee_id"] == "alice"
    assert claim["amount"] == Decimal("850")
    assert claim["currency"] == "NOK"
    assert claim["receipt_image"] == "receipt.jpg"

    # ...and the ledger learned about it
    assert service.ledger.month_total(Office.OSLO, 2026, 11) == Decimal("850")

    # HR approves days later
    clock.advance(days=6)
    hr.approve(refill.hr_claim_id)
    assert refill.state is RefillState.REIMBURSED
    assert any("approved" in m for m in chat.messages_to("alice"))


def test_visitor_claims_in_purchase_currency_not_payroll_currency(chat, hr, clock):
    """Oslo employee visiting Bengaluru pays INR; the claim is filed in INR.
    HR reimburses in payroll currency (NOK) — conversion is HR's job."""
    from snack.lifecycle import SnackService

    visitor = Volunteer(
        id="viggo", name="Viggo", office=Office.OSLO,
        payroll_currency="NOK", visiting=Office.BENGALURU,
    )
    service = SnackService([visitor], chat, hr, now=clock)

    refill = service.report_empty(Office.BENGALURU)
    assert refill.assignee_id == "viggo"
    service.claim(refill.id, "viggo")
    service.submit_receipt(refill.id, "viggo", Decimal("2200"), "snacks", "r.jpg")

    assert hr.claims[refill.hr_claim_id]["currency"] == "INR"
    assert service.ledger.month_total(Office.BENGALURU, 2026, 11) == Decimal("2200")


def test_over_budget_purchase_still_reimbursed_but_flagged(service, chat, clock):
    for i in range(6):  # 6 x 1100 NOK = 6600 > 6000 budget
        refill = service.report_empty(Office.OSLO)
        buyer = refill.assignee_id
        service.claim(refill.id, buyer)
        refill = service.submit_receipt(
            refill.id, buyer, Decimal("1100"), "snacks", "r.jpg"
        )
        clock.advance(days=1)

    assert refill.state is RefillState.SUBMITTED  # volunteer is made whole
    assert any(to == "#snacks-admin" for to, _ in chat.sent)  # admin warned
    assert service.ledger.monthly_report(2026, 11)["oslo"]["over_budget"] is True


def test_new_refill_possible_while_old_claim_awaits_hr(service):
    refill = service.report_empty(Office.OSLO)
    service.claim(refill.id, "alice")
    service.submit_receipt(refill.id, "alice", Decimal("500"), "snacks", "r.jpg")

    # box runs empty again before HR approves the old claim
    second = service.report_empty(Office.OSLO)
    assert second is not refill
