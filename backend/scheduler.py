from datetime import datetime, time, timedelta
from uuid import uuid4

from sqlalchemy import select, text

from backend.config import get_settings
from backend.database.models import Appointment, SessionLocal
from backend.timeutil import as_office_time, as_utc, office_zone
from backend.tools.calendar import calendar_service
from backend.tools.emailer import send_booking_confirmation

CONSULTATIONS = {
    "Initial Consultation": 30,
    "Follow-up Consultation": 30,
    "Detailed Case Consultation": 60,
}


class BookingConflict(ValueError):
    """Raised when a requested slot is no longer free."""


def duration_for(consultation_type: str) -> int:
    if consultation_type not in CONSULTATIONS:
        raise ValueError("Choose one of the available consultation types.")
    return CONSULTATIONS[consultation_type]


def _clock(value: str) -> time:
    return time.fromisoformat(value)


def is_working_time(start: datetime, end: datetime) -> bool:
    settings = get_settings()
    start = as_office_time(start)
    end = as_office_time(end)
    if start.weekday() > 4 or start.date() != end.date():
        return False
    day_start, day_end = _clock(settings.working_day_start), _clock(settings.working_day_end)
    lunch_start, lunch_end = _clock(settings.lunch_start), _clock(settings.lunch_end)
    start_clock, end_clock = start.time(), end.time()
    if not (day_start <= start_clock and end_clock <= day_end):
        return False
    return end_clock <= lunch_start or start_clock >= lunch_end


def _overlaps(existing_start: datetime, existing_end: datetime, start: datetime, end: datetime) -> bool:
    return as_utc(existing_start) < as_utc(end) and as_utc(existing_end) > as_utc(start)


def validate_bookable_start(start: datetime) -> datetime:
    settings = get_settings()
    start = as_office_time(start)
    if start.second or start.microsecond:
        raise ValueError("Please choose a time with minute precision; seconds are not supported.")
    if start <= datetime.now(office_zone()):
        raise ValueError("Please choose a future appointment time.")
    if start.minute % settings.slot_interval_minutes:
        raise ValueError(f"Appointments must start on a {settings.slot_interval_minutes}-minute interval.")
    return start


def is_available(start: datetime, minutes: int, session=None) -> bool:
    start = validate_bookable_start(start)
    end = start + timedelta(minutes=minutes)
    if not is_working_time(start, end):
        return False
    owns_session = session is None
    if owns_session:
        session = SessionLocal()
    try:
        local = session.scalars(
            select(Appointment).where(Appointment.starts_at < as_utc(end), Appointment.ends_at > as_utc(start))
        ).first()
    finally:
        if owns_session:
            session.close()
    if local:
        return False
    return not any(_overlaps(busy_start, busy_end, start, end) for busy_start, busy_end in calendar_service.busy_periods(start, end))


def suggest_slots(preferred_start: datetime, consultation_type: str, count: int = 3) -> list[datetime]:
    minutes = duration_for(consultation_type)
    interval = get_settings().slot_interval_minutes
    now = datetime.now(office_zone())
    candidate = max(as_office_time(preferred_start), now).replace(second=0, microsecond=0)
    extra = (-candidate.minute) % interval
    candidate += timedelta(minutes=extra)
    if candidate <= now:
        candidate += timedelta(minutes=interval)
    slots: list[datetime] = []
    attempts = max(1, (14 * 24 * 60) // interval)
    for _ in range(attempts):
        if is_available(candidate, minutes):
            slots.append(candidate)
            if len(slots) == count:
                return slots
        candidate += timedelta(minutes=interval)
    return slots


def _acquire_lock(session) -> None:
    settings = get_settings()
    if settings.is_sqlite:
        session.execute(text("SELECT 1"))
        return
    # One transaction-scoped lock serializes booking decisions, including
    # partially overlapping appointments that have different start times.
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": 1212246849})


def book(client_name: str, client_email: str, consultation_type: str, start: datetime) -> Appointment:
    minutes = duration_for(consultation_type)
    start = validate_bookable_start(start)
    end = start + timedelta(minutes=minutes)
    utc_start, utc_end = as_utc(start), as_utc(end)
    event_id = None
    try:
        with SessionLocal() as session:
            with session.begin():
                _acquire_lock(session)
                if not is_available(start, minutes, session=session):
                    raise BookingConflict("This time is no longer available. Please choose another slot.")
                placeholder = f"pending-{uuid4()}"
                appointment = Appointment(
                    client_name=client_name.strip(),
                    client_email=client_email.strip().lower(),
                    consultation_type=consultation_type,
                    starts_at=utc_start,
                    ends_at=utc_end,
                    calendar_event_id=placeholder,
                )
                session.add(appointment)
                session.flush()
                event_id = calendar_service.create_event(
                    f"{consultation_type} — {client_name}", start, end, client_email
                )
                appointment.calendar_event_id = event_id
                session.flush()
                session.refresh(appointment)
                booked = appointment
    except Exception:
        if event_id:
            calendar_service.delete_event(event_id)
        raise
    send_booking_confirmation(client_name, client_email, consultation_type, start, end)
    return booked
