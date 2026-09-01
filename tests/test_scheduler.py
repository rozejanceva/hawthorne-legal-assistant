from datetime import datetime

from backend.scheduler import is_working_time, suggest_slots
from backend.timeutil import as_office_time


def test_back_to_back_and_lunch_rules():
    assert is_working_time(datetime(2026, 8, 26, 14, 30), datetime(2026, 8, 26, 15, 30))
    assert not is_working_time(datetime(2026, 8, 26, 11, 30), datetime(2026, 8, 26, 12, 30))
    assert not is_working_time(datetime(2026, 8, 29, 10, 0), datetime(2026, 8, 26, 10, 30))
    assert not is_working_time(datetime(2026, 8, 29, 10, 0), datetime(2026, 8, 29, 10, 30))


def test_office_timezone_from_utc():
    start = as_office_time(datetime.fromisoformat("2026-08-26T08:00:00+00:00"))
    end = as_office_time(datetime.fromisoformat("2026-08-26T08:30:00+00:00"))
    assert start.hour == 10
    assert is_working_time(start, end)


def test_suggests_slots_after_lunch_when_needed():
    slots = suggest_slots(datetime(2026, 8, 26, 11, 45), "Initial Consultation")
    assert slots
    assert slots[0].hour >= 13
