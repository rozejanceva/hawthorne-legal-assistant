from datetime import datetime
from zoneinfo import ZoneInfo

from backend.config import get_settings


def office_zone() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def as_office_time(value: datetime) -> datetime:
    """Treat naive datetimes as office-local; convert aware values into the office zone."""
    zone = office_zone()
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def as_utc(value: datetime) -> datetime:
    return as_office_time(value).astimezone(ZoneInfo("UTC"))


def rfc3339(value: datetime) -> str:
    return as_utc(value).isoformat().replace("+00:00", "Z")
