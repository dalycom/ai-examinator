from collections.abc import Awaitable, Callable

import redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.enums import AppEnv


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed fixed-window rate limiter for auth and API routes."""

    AUTH_PATHS = ("/api/v1/auth/login", "/api/v1/auth/register-organization", "/api/v1/auth/refresh")

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self._redis: redis.Redis | None = None

    def _client(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _limit_for_path(self, path: str) -> tuple[int, int] | None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return None
        if path in self.AUTH_PATHS:
            return settings.rate_limit_auth_per_minute, 60
        if path.startswith("/api/v1/"):
            return settings.rate_limit_api_per_minute, 60
        return None

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if settings.app_env == AppEnv.CI or not settings.rate_limit_enabled:
            return await call_next(request)

        limit_config = self._limit_for_path(request.url.path)
        if limit_config is None:
            return await call_next(request)

        max_requests, window_seconds = limit_config
        bucket = f"rate:{request.url.path}:{self._client_ip(request)}"
        try:
            count = self._client().incr(bucket)
            if count == 1:
                self._client().expire(bucket, window_seconds)
        except redis.RedisError:
            return await call_next(request)

        if count > max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "https://errors.ai-examinator/rate_limit_exceeded",
                    "title": "Too many requests",
                    "status": 429,
                    "code": "RATE_LIMIT_EXCEEDED",
                    "detail": "Rate limit exceeded. Try again later.",
                    "errors": {"retry_after_seconds": window_seconds},
                },
                headers={"Retry-After": str(window_seconds)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - count))
        return response
