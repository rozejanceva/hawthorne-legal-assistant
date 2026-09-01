import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.assistant import respond
from backend.config import ROOT_DIR, get_settings
from backend.database.models import Appointment, SessionLocal, init_db
from backend.middleware import RateLimitMiddleware
from backend.scheduler import CONSULTATIONS, BookingConflict, book, duration_for, is_available, suggest_slots
from backend.schemas import AppointmentOut, AvailabilityRequest, BookingRequest, ChatRequest, ChatResponse, LoginRequest
from backend.timeutil import as_office_time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
api = APIRouter(prefix="/api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="legal_admin",
        https_only=settings.is_production and settings.secure_cookies,
        same_site="strict",
        max_age=60 * 60 * 8,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    if settings.is_production:
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list())
    application.include_router(api)

    @application.get("/healthz")
    def healthz():
        return {"status": "ok"}

    if FRONTEND_DIST.exists():
        assets = FRONTEND_DIST / "assets"
        if assets.exists():
            application.mount("/assets", StaticFiles(directory=assets), name="assets")

        @application.get("/{path:path}")
        def spa(path: str):
            if path.startswith("api/") or path in {"api", "docs", "openapi.json", "redoc"}:
                raise HTTPException(status_code=404, detail="Not found")
            candidate = FRONTEND_DIST / path
            if path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return application


app = create_app()


def require_admin(request: Request) -> None:
    if not request.session.get("admin"):
        raise HTTPException(status_code=401, detail="Admin sign-in required.")


@api.get("/health")
def health():
    settings = get_settings()
    return {"status": "ok", "calendar_mode": settings.calendar_mode, "env": settings.app_env}


@api.get("/public-config")
def public_config():
    settings = get_settings()
    return {
        "timezone": settings.timezone,
        "working_day_start": settings.working_day_start,
        "working_day_end": settings.working_day_end,
        "lunch_start": settings.lunch_start,
        "lunch_end": settings.lunch_end,
        "consultations": CONSULTATIONS,
    }


@api.get("/consultation-types")
def consultation_types():
    return CONSULTATIONS


@api.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    return {"message": respond(payload.message)}


@api.post("/availability")
def availability(payload: AvailabilityRequest):
    try:
        minutes = duration_for(payload.consultation_type)
        start = as_office_time(payload.preferred_start)
        if is_available(start, minutes):
            return {"available": True, "slots": [start.isoformat()]}
        return {
            "available": False,
            "slots": [slot.isoformat() for slot in suggest_slots(start, payload.consultation_type)],
        }
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: BookingRequest):
    try:
        return book(payload.client_name, str(payload.client_email), payload.consultation_type, payload.starts_at)
    except BookingConflict as exc:
        logger.info("Booking rejected: %s", exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        logger.info("Booking rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api.post("/admin/login")
def admin_login(payload: LoginRequest, request: Request):
    settings = get_settings()
    valid_user = secrets.compare_digest(payload.username.encode(), settings.admin_username.encode()) if len(payload.username) == len(settings.admin_username) else False
    valid_pass = secrets.compare_digest(payload.password.encode(), settings.admin_password.encode()) if len(payload.password) == len(settings.admin_password) else False
    valid = valid_user and valid_pass
    if not valid:
        raise HTTPException(status_code=401, detail="Incorrect admin credentials")
    request.session["admin"] = True
    return {"ok": True}


@api.post("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@api.get("/admin/session")
def admin_session(request: Request):
    return {"authenticated": bool(request.session.get("admin"))}


@api.get("/admin/appointments", response_model=list[AppointmentOut], dependencies=[Depends(require_admin)])
def list_appointments():
    with SessionLocal() as session:
        rows = session.scalars(select(Appointment).order_by(Appointment.starts_at)).all()
        return [AppointmentOut.model_validate(row) for row in rows]
