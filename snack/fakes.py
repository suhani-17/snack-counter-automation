"""Simulated stand-ins for the company chat tool and the external HR system.
In production these become a chat-bot webhook and an HTTP client."""
from itertools import count


class FakeChat:
    def __init__(self):
        self.sent = []  # (recipient, text)

    def send(self, to: str, text: str) -> None:
        self.sent.append((to, text))

    def messages_to(self, recipient: str) -> list:
        return [text for to, text in self.sent if to == recipient]


class FakeHR:
    """HR approves claims 1-10 days later; tests trigger approval explicitly."""

    def __init__(self):
        self.claims = {}
        self._seq = count(1)
        self.on_approved = lambda claim_id: None  # wired up by SnackService

    def submit_claim(self, employee_id, amount, currency, description, receipt_image) -> str:
        claim_id = f"hr-{next(self._seq)}"
        self.claims[claim_id] = {
            "employee_id": employee_id,
            "amount": amount,
            "currency": currency,
            "description": description,
            "receipt_image": receipt_image,
            "status": "pending",
        }
        return claim_id

    def approve(self, claim_id: str) -> None:
        self.claims[claim_id]["status"] = "approved"
        self.on_approved(claim_id)
