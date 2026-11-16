"""Purchase ledger: monthly totals, remaining budget, the management report."""
from datetime import datetime
from decimal import Decimal

from .models import BUDGETS, Office, Purchase


class Ledger:
    def __init__(self):
        self.purchases: list[Purchase] = []

    def add(self, purchase: Purchase) -> None:
        self.purchases.append(purchase)

    def month_total(self, office: Office, year: int, month: int) -> Decimal:
        return sum(
            (
                p.amount
                for p in self.purchases
                if p.office is office
                and p.purchased_at.year == year
                and p.purchased_at.month == month
            ),
            Decimal("0"),
        )

    def remaining(self, office: Office, when: datetime) -> Decimal:
        budget, _ = BUDGETS[office]
        return budget - self.month_total(office, when.year, when.month)

    def monthly_report(self, year: int, month: int) -> dict:
        """One report across both offices. Totals stay in each office's own
        currency — we don't invent an FX rate (see DESIGN.md)."""
        report = {}
        for office, (budget, currency) in BUDGETS.items():
            total = self.month_total(office, year, month)
            report[office.value] = {
                "total": total,
                "currency": currency,
                "budget": budget,
                "over_budget": total > budget,
                "purchases": [
                    f"{p.purchased_at.date()} {p.amount} {p.currency} — {p.description}"
                    for p in self.purchases
                    if p.office is office
                    and p.purchased_at.year == year
                    and p.purchased_at.month == month
                ],
            }
        return report
