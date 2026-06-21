from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.i18n import translate


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message_key: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message_key = message_key
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message_key)


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message_key: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    locale = getattr(request.state, "locale", "en")
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"https://errors.ai-examinator/{code.lower()}",
            "title": translate(message_key, locale),
            "status": status_code,
            "code": code,
            "detail": translate(message_key, locale),
            "errors": details or {},
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message_key=exc.message_key,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(
        request=request,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message_key="errors.http_error",
        details={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message_key="errors.validation_failed",
        details={"errors": exc.errors()},
    )
