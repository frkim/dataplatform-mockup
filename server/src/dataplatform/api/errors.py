"""RFC 9457 ``application/problem+json`` error responses."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from dataplatform.domain.errors import DomainError
from dataplatform.logging_config import correlation_id

logger = logging.getLogger(__name__)

PROBLEM_TYPE_BASE = "https://dataplatform-mockup.dev/problems/"
PROBLEM_CONTENT_TYPE = "application/problem+json"


def problem(request: Request, status: int, title: str, detail: str, type_suffix: str, **extra: Any) -> JSONResponse:
    """Build a problem response carrying the request correlation id as ``traceId``."""
    body = {
        "type": PROBLEM_TYPE_BASE + type_suffix,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "traceId": correlation_id.get(),
        **extra,
    }
    return JSONResponse(body, status_code=status, media_type=PROBLEM_CONTENT_TYPE)


def _format_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    return [
        {"location": ".".join(str(p) for p in err.get("loc", ())), "message": err.get("msg", "invalid")}
        for err in exc.errors()
    ]


def install_error_handlers(app: FastAPI) -> None:
    """Map domain, validation, HTTP and unexpected errors to problem responses."""

    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        return problem(request, exc.status_code, exc.title, exc.detail, exc.type_suffix)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = _format_validation_errors(exc)
        detail = "; ".join(f"{e['location']}: {e['message']}" for e in errors)
        return problem(request, 400, "Validation failed", detail, "validation", errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(request, exc.status_code, str(exc.detail), str(exc.detail), f"http-{exc.status_code}")

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"event": "request.error", "path": request.url.path})
        return problem(request, 500, "Internal server error", "An unexpected error occurred.", "internal")
