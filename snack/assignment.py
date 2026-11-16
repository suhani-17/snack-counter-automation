"""Who should buy: the available volunteer at the office who bought least recently."""
from datetime import datetime
from typing import Iterable, Optional

from .models import Office, Volunteer

_NEVER = datetime.min  # never-purchased sorts first


def pick_volunteer(
    volunteers: Iterable[Volunteer],
    office: Office,
    exclude: Iterable[str] = (),
) -> Optional[Volunteer]:
    exclude = set(exclude)
    candidates = [
        v
        for v in volunteers
        if v.present_office is office and v.available and v.id not in exclude
    ]
    return min(
        candidates, key=lambda v: v.last_purchase_at or _NEVER, default=None
    )
