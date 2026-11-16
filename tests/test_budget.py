from datetime import datetime
from decimal import Decimal

from snack.budget import Ledger
from snack.models import Office, Purchase


def buy(office, amount, currency, when, buyer="v1", desc="snacks"):
    return Purchase(
        buyer_id=buyer,
        office=office,
        amount=Decimal(amount),
        currency=currency,
        description=desc,
        receipt_image="receipt.jpg",
        purchased_at=when,
    )


NOV = datetime(2026, 11, 5)


def test_totals_never_mix_currencies():
    ledger = Ledger()
    ledger.add(buy(Office.OSLO, "800", "NOK", NOV))
    ledger.add(buy(Office.OSLO, "450.50", "NOK", NOV))
    ledger.add(buy(Office.BENGALURU, "2000", "INR", NOV))
    assert ledger.month_total(Office.OSLO, 2026, 11) == Decimal("1250.50")
    assert ledger.month_total(Office.BENGALURU, 2026, 11) == Decimal("2000")


def test_other_months_excluded():
    ledger = Ledger()
    ledger.add(buy(Office.OSLO, "500", "NOK", datetime(2026, 10, 31)))
    ledger.add(buy(Office.OSLO, "700", "NOK", NOV))
    assert ledger.month_total(Office.OSLO, 2026, 11) == Decimal("700")


def test_remaining_budget():
    ledger = Ledger()
    ledger.add(buy(Office.OSLO, "1200", "NOK", NOV))
    assert ledger.remaining(Office.OSLO, NOV) == Decimal("4800")
    assert ledger.remaining(Office.BENGALURU, NOV) == Decimal("15000")


def test_report_covers_both_offices_and_flags_overrun():
    ledger = Ledger()
    for _ in range(6):  # 6 x 1100 = 6600 NOK > 6000 budget
        ledger.add(buy(Office.OSLO, "1100", "NOK", NOV))
    ledger.add(buy(Office.BENGALURU, "3000", "INR", NOV))

    report = ledger.monthly_report(2026, 11)
    assert report["oslo"]["total"] == Decimal("6600")
    assert report["oslo"]["currency"] == "NOK"
    assert report["oslo"]["over_budget"] is True
    assert report["bengaluru"]["total"] == Decimal("3000")
    assert report["bengaluru"]["over_budget"] is False
    assert len(report["oslo"]["purchases"]) == 6
