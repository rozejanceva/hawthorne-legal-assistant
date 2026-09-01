import logging
from collections import defaultdict, deque
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import get_settings

logger = logging.getLogger(__name__)
LIMITED_PATHS = {"/api/chat", "/api/availability", "/api/appointments", "/api/admin/login"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path not in LIMITED_PATHS:
            return await call_next(request)
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        now = monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            logger.warning("Rate limit exceeded for %s", key)
            return JSONResponse({"detail": "Too many requests. Please wait a minute and try again."}, status_code=429)
        window.append(now)
        return await call_next(request)
