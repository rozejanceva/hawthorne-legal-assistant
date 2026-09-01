import logging
from datetime import datetime

from backend.config import get_settings
from backend.timeutil import as_office_time, rfc3339

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Calendar boundary. Google credentials never reach the browser."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def busy_periods(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        if self.settings.calendar_mode == "google":
            return self._google_busy_periods(start, end)
        return []

    def create_event(self, title: str, start: datetime, end: datetime, attendee: str) -> str:
        if self.settings.calendar_mode == "google":
            return self._google_create_event(title, start, end, attendee)
        from uuid import uuid4
        return f"demo-{uuid4()}"

    def delete_event(self, event_id: str) -> None:
        if self.settings.calendar_mode != "google" or not event_id or event_id.startswith("demo-"):
            return
        try:
            self._google_service().events().delete(
                calendarId=self.settings.google_calendar_id,
                eventId=event_id,
                sendUpdates="all",
            ).execute()
        except Exception:
            logger.exception("Failed to delete orphan Google Calendar event %s", event_id)

    def _google_service(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("Google Calendar packages are not installed.") from exc

        token_path = self.settings.google_token_path()
        credentials_path = self.settings.google_credentials_path()
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES) if token_path.exists() else None
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                token_path.write_text(credentials.to_json(), encoding="utf-8")
            elif self.settings.google_allow_browser_oauth:
                if not credentials_path.exists():
                    raise RuntimeError(f"Missing Google OAuth client file: {credentials_path}")
                credentials = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES).run_local_server(port=0)
                token_path.write_text(credentials.to_json(), encoding="utf-8")
            else:
                raise RuntimeError(
                    "Google Calendar is not authorized. Place a valid token.json on the server, "
                    "or run once locally with GOOGLE_ALLOW_BROWSER_OAUTH=true."
                )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def _google_busy_periods(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        service = self._google_service()
        response = service.freebusy().query(body={
            "timeMin": rfc3339(start),
            "timeMax": rfc3339(end),
            "timeZone": self.settings.timezone,
            "items": [{"id": self.settings.google_calendar_id}],
        }).execute()
        calendar = response["calendars"][self.settings.google_calendar_id]
        if calendar.get("errors"):
            raise RuntimeError(f"Google Calendar free/busy error: {calendar['errors']}")
        periods = []
        for item in calendar.get("busy", []):
            busy_start = as_office_time(datetime.fromisoformat(item["start"].replace("Z", "+00:00")))
            busy_end = as_office_time(datetime.fromisoformat(item["end"].replace("Z", "+00:00")))
            periods.append((busy_start, busy_end))
        return periods

    def _google_create_event(self, title: str, start: datetime, end: datetime, attendee: str) -> str:
        office_start, office_end = as_office_time(start), as_office_time(end)
        service = self._google_service()
        event = service.events().insert(
            calendarId=self.settings.google_calendar_id,
            body={
                "summary": title,
                "description": "Booked through the Hawthorne Legal scheduling assistant.",
                "start": {"dateTime": office_start.isoformat(), "timeZone": self.settings.timezone},
                "end": {"dateTime": office_end.isoformat(), "timeZone": self.settings.timezone},
                "attendees": [{"email": attendee}],
            },
            sendUpdates="all",
        ).execute()
        return event["id"]


calendar_service = CalendarService()
