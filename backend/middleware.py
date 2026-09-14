import logging
from collections import defaultdict, deque
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import get_settings

logger = logging.getLogger(__name__)
LIMITED_PATHS = {"/api/chat", "/api/availability", "/api/appointments", "/api/admin/login"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; "
            "img-src 'self' data:; script-src 'self'; connect-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:"
        )
        settings = get_settings()
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith(("/api/admin", "/admin")):
            response.headers["Cache-Control"] = "no-store"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = monotonic()

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path not in LIMITED_PATHS:
            return await call_next(request)
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        now = monotonic()
        if now - self._last_cleanup > 60:
            cutoff = now - 60
            for stored_key, stored_window in list(self._hits.items()):
                while stored_window and stored_window[0] < cutoff:
                    stored_window.popleft()
                if not stored_window:
                    self._hits.pop(stored_key, None)
            self._last_cleanup = now
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            logger.warning("Rate limit exceeded for %s", key)
            return JSONResponse({"detail": "Too many requests. Please wait a minute and try again."}, status_code=429)
        window.append(now)
        return await call_next(request)
