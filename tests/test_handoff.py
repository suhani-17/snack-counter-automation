from snack.models import Office, RefillState


def test_silent_candidate_is_skipped_after_ask_timeout(service, clock, chat):
    refill = service.report_empty(Office.OSLO)
    first_asked = refill.assignee_id

    clock.advance(hours=5)  # past ASK_TIMEOUT, nobody claimed
    service.check_timeouts()

    assert refill.state is RefillState.EMPTY
    assert refill.assignee_id != first_asked
    assert first_asked in refill.asked  # won't be asked again for this refill


def test_abandoned_claim_is_handed_to_someone_else(service, clock):
    refill = service.report_empty(Office.OSLO)
    service.claim(refill.id, "alice")

    clock.advance(hours=25)  # past CLAIM_TIMEOUT, no receipt
    service.check_timeouts()

    assert refill.state is RefillState.EMPTY
    assert refill.assignee_id is not None
    assert refill.assignee_id != "alice"


def test_timeout_does_not_fire_early(service, clock):
    refill = service.report_empty(Office.OSLO)
    service.claim(refill.id, "alice")

    clock.advance(hours=23)
    service.check_timeouts()

    assert refill.state is RefillState.CLAIMED
    assert refill.assignee_id == "alice"


def test_everyone_exhausted_escalates_to_channel(service, clock, chat):
    refill = service.report_empty(Office.OSLO)
    for _ in range(3):  # burn through all three Oslo volunteers
        clock.advance(hours=5)
        service.check_timeouts()

    assert refill.assignee_id is None
    assert any("#snacks-oslo" == to for to, _ in chat.sent)


def test_fairness_rotates_buyers(service, clock):
    """Whoever bought last goes to the back of the queue."""
    refill = service.report_empty(Office.OSLO)
    buyer = refill.assignee_id
    service.claim(refill.id, buyer)
    service.submit_receipt(refill.id, buyer, 600, "fruit and nuts", "r.jpg")

    clock.advance(days=3)
    next_refill = service.report_empty(Office.OSLO)
    assert next_refill.assignee_id != buyer
