import logging
import smtplib
from email.message import EmailMessage

from backend.config import get_settings
from backend.timeutil import as_office_time

logger = logging.getLogger(__name__)


def send_booking_confirmation(client_name: str, client_email: str, consultation_type: str, starts_at, ends_at) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        logger.info("SMTP is not configured; skipping booking email to %s", client_email)
        return
    start = as_office_time(starts_at)
    end = as_office_time(ends_at)
    when = start.strftime("%A, %d %B %Y at %H:%M")
    until = end.strftime("%H:%M")
    message = EmailMessage()
    message["Subject"] = f"Consultation confirmed — {consultation_type}"
    message["From"] = settings.smtp_from
    message["To"] = client_email
    message.set_content(
        f"Dear {client_name},\n\n"
        f"Your {consultation_type} is confirmed for {when}–{until} ({settings.timezone}).\n\n"
        "If you need to change this appointment, please contact the office.\n\n"
        "Hawthorne Legal\n"
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        logger.info("Sent booking confirmation to %s", client_email)
    except Exception:
        logger.exception("Failed to send booking confirmation to %s", client_email)
