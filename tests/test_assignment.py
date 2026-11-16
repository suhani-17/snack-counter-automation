from datetime import datetime

from snack.assignment import pick_volunteer
from snack.models import Office, Volunteer


def v(id, office=Office.OSLO, **kw):
    return Volunteer(id=id, name=id, office=office, payroll_currency="NOK", **kw)


def test_least_recently_purchased_wins():
    recent = v("recent", last_purchase_at=datetime(2026, 11, 10))
    stale = v("stale", last_purchase_at=datetime(2026, 1, 1))
    assert pick_volunteer([recent, stale], Office.OSLO) is stale


def test_never_purchased_beats_everyone():
    veteran = v("veteran", last_purchase_at=datetime(2026, 1, 1))
    rookie = v("rookie")
    assert pick_volunteer([veteran, rookie], Office.OSLO) is rookie


def test_unavailable_and_other_office_excluded():
    holiday = v("holiday", available=False)
    abroad = v("abroad", office=Office.BENGALURU)
    assert pick_volunteer([holiday, abroad], Office.OSLO) is None


def test_visitor_counts_at_visited_office():
    visitor = v("visitor", office=Office.OSLO, visiting=Office.BENGALURU)
    assert pick_volunteer([visitor], Office.BENGALURU) is visitor
    assert pick_volunteer([visitor], Office.OSLO) is None


def test_explicit_exclusion():
    only = v("only")
    assert pick_volunteer([only], Office.OSLO, exclude=["only"]) is None
