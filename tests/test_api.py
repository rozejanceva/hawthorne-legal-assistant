from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.main import app


client = TestClient(app)


def test_health_and_public_config():
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
        "starts_at": "2026-08-26T15:00:00",
    }
    available = client.post(
        "/api/availability",
        json={"consultation_type": payload["consultation_type"], "preferred_start": payload["starts_at"]},
    )
    assert available.status_code == 200
    booked = client.post("/api/appointments", json=payload)
    assert booked.status_code == 201
    conflict = client.post("/api/appointments", json=payload)
    assert conflict.status_code == 409
