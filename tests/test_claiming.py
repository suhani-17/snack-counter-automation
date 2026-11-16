import pytest

from snack.lifecycle import AlreadyClaimed, InvalidTransition
from snack.models import Office, RefillState


def test_two_people_cannot_claim_the_same_refill(service):
    refill = service.report_empty(Office.OSLO)
    service.claim(refill.id, "alice")
    with pytest.raises(AlreadyClaimed):
        service.claim(refill.id, "bjorn")
    assert refill.assignee_id == "alice"
    assert refill.state is RefillState.CLAIMED


def test_duplicate_empty_reports_attach_to_one_refill(service):
    first = service.report_empty(Office.OSLO)
    second = service.report_empty(Office.OSLO)
    assert first is second
    assert len(service.refills) == 1


def test_offices_are_independent(service):
    oslo = service.report_empty(Office.OSLO)
    blr = service.report_empty(Office.BENGALURU)
    assert oslo is not blr


def test_anyone_present_can_claim_not_just_the_asked_person(service):
    refill = service.report_empty(Office.OSLO)
    asked = refill.assignee_id
    other = next(v for v in ("alice", "bjorn", "carl") if v != asked)
    service.claim(refill.id, other)
    assert refill.assignee_id == other


def test_only_the_claimer_may_submit_the_receipt(service):
    refill = service.report_empty(Office.OSLO)
    service.claim(refill.id, "alice")
    with pytest.raises(InvalidTransition):
        service.submit_receipt(refill.id, "bjorn", 500, "chips", "r.jpg")
