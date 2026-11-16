from datetime import datetime, timedelta

import pytest

from snack.fakes import FakeChat, FakeHR
from snack.lifecycle import SnackService
from snack.models import Office, Volunteer


class Clock:
    """Injectable clock so timeout rules are testable without sleeping."""

    def __init__(self, start=datetime(2026, 11, 2, 9, 0)):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, **kwargs):
        self.t += timedelta(**kwargs)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def volunteers():
    return [
        Volunteer(id="alice", name="Alice", office=Office.OSLO, payroll_currency="NOK"),
        Volunteer(id="bjorn", name="Bjørn", office=Office.OSLO, payroll_currency="NOK"),
        Volunteer(id="carl", name="Carl", office=Office.OSLO, payroll_currency="NOK"),
        Volunteer(id="divya", name="Divya", office=Office.BENGALURU, payroll_currency="INR"),
        Volunteer(id="esha", name="Esha", office=Office.BENGALURU, payroll_currency="INR"),
    ]


@pytest.fixture
def chat():
    return FakeChat()


@pytest.fixture
def hr():
    return FakeHR()


@pytest.fixture
def service(volunteers, chat, hr, clock):
    return SnackService(volunteers, chat, hr, now=clock)
