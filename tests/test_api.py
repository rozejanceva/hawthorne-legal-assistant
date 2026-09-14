from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.main import app


client = TestClient(app)


def test_health_and_public_config():
    readiness = client.get("/healthz")
    assert readiness.status_code == 200
    assert readiness.headers["x-content-type-options"] == "nosniff"
    assert readiness.headers["x-frame-options"] == "DENY"
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    config = client.get("/api/public-config")
    assert config.status_code == 200
    assert "timezone" in config.json()


def test_admin_requires_login():
    denied = client.get("/api/admin/appointments")
    assert denied.status_code == 401
    settings = get_settings()
    login = client.post("/api/admin/login", json={"username": settings.admin_username, "password": settings.admin_password})
    assert login.status_code == 200
    listed = client.get("/api/admin/appointments")
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)


def test_booking_creates_appointment():
    payload = {
        "client_name": "Jane Smith",
        "client_email": "jane@example.com",
        "consultation_type": "Initial Consultation",
        "starts_at": "2030-08-26T15:00:00",
    }
    available = client.post(
        "/api/availability",
        json={"consultation_type": payload["consultation_type"], "preferred_start": payload["starts_at"]},
    )
    assert available.status_code == 200
    booked = client.post("/api/appointments", json=payload)
    assert booked.status_code == 201
    assert "client_email" not in booked.json()
    assert "calendar_event_id" not in booked.json()
    conflict = client.post("/api/appointments", json=payload)
    assert conflict.status_code == 409


def test_rejects_past_and_off_grid_appointments():
    base = {
        "client_name": "Jane Smith",
        "client_email": "jane@example.com",
        "consultation_type": "Initial Consultation",
    }
    past = client.post("/api/appointments", json={**base, "starts_at": "2020-01-06T10:00:00"})
    assert past.status_code == 400
    off_grid = client.post("/api/appointments", json={**base, "starts_at": "2030-08-26T10:07:00"})
    assert off_grid.status_code == 400


def test_rejects_blank_user_content():
    chat = client.post("/api/chat", json={"message": "   "})
    assert chat.status_code == 422
    booking = client.post("/api/appointments", json={
        "client_name": "  ",
        "client_email": "jane@example.com",
        "consultation_type": "Initial Consultation",
        "starts_at": "2030-08-26T10:00:00",
    })
    assert booking.status_code == 422
