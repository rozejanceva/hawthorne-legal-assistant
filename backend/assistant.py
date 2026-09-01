"""Safe conversation layer for the public scheduling widget."""

from backend.scheduler import CONSULTATIONS

LEGAL_WORDS = ("sue", "lawsuit", "legal advice", "should i", "rights", "win my case", "divorce", "contract", "criminal")


def fallback_reply(message: str) -> str:
    text = message.lower()
    if any(word in text for word in LEGAL_WORDS):
        return "I’m the office scheduling assistant, so I can’t provide legal advice or assess your situation. I can help you arrange a confidential consultation with the lawyer."
    if any(word in text for word in ("price", "cost", "fee", "rate")):
        return "Consultation fees depend on the matter. Please schedule a consultation and the office can explain the applicable fees before you proceed."
    if any(word in text for word in ("hour", "open", "working", "lunch")):
        return "Appointments are normally available Monday through Friday, 9:00 AM to 5:00 PM, excluding the configured lunch break. The scheduler will show the current available times."
    if any(word in text for word in ("type", "consultation", "appointment", "book", "schedule")):
        types = ", ".join(f"{name} ({minutes} minutes)" for name, minutes in CONSULTATIONS.items())
        return f"I can help with {types}. Use the booking form below to choose a preferred time, and I’ll show only available slots."
    return "I can help you schedule a consultation, explain the appointment types, or check available times. I can’t provide legal advice, but I can help you connect with the office."


def respond(message: str) -> str:
    """Use OpenAI for natural scheduling responses when configured; otherwise stay useful locally."""
    # Legal advice is always handled by the deterministic guardrail above.
    if any(word in message.lower() for word in LEGAL_WORDS):
        return fallback_reply(message)
    try:
        from openai import OpenAI
        from backend.config import get_settings

        settings = get_settings()
        if not settings.openai_api_key:
            return fallback_reply(message)
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            instructions=(
                "You are a friendly law-office scheduling assistant. You may answer only questions about "
                "the office's appointment scheduling, consultation types, normal availability, and the booking process. "
                "Never provide legal advice, legal analysis, or assess a case. If asked anything legal, say you cannot "
                "provide legal advice and offer to schedule a confidential consultation. Keep answers to three sentences or fewer."
            ),
            input=message,
        )
        return response.output_text or fallback_reply(message)
    except Exception:
        return fallback_reply(message)
