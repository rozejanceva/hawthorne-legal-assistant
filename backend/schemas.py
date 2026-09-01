from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.timeutil import as_office_time


def _minute_precision(value: datetime) -> datetime:
    office = as_office_time(value)
    if office.second or office.microsecond:
        raise ValueError("Please choose a time with minute precision; seconds are not supported.")
    return office


class AvailabilityRequest(BaseModel):
    consultation_type: str
    preferred_start: datetime

    @field_validator("preferred_start")
    @classmethod
    def minute_precision_only(cls, value: datetime) -> datetime:
        return _minute_precision(value)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)


class ChatResponse(BaseModel):
    message: str


class BookingRequest(BaseModel):
    client_name: str = Field(min_length=2, max_length=120)
    client_email: EmailStr
    consultation_type: str
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def minute_precision_only(cls, value: datetime) -> datetime:
        return _minute_precision(value)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class AppointmentOut(BaseModel):
    id: int
    client_name: str
    client_email: str
    consultation_type: str
    starts_at: datetime
    ends_at: datetime
    calendar_event_id: str

    model_config = {"from_attributes": True}
