"""ASGI middleware: correlation id, security headers, and protocol on/off switches."""

import json
import uuid
from collections.abc import Callable
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from dataplatform.logging_config import correlation_id

CORRELATION_HEADER = "x-correlation-id"
_STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
# Swagger UI / ReDoc load their assets from jsDelivr.
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'"
)
_DOCS_PATHS = ("/docs", "/redoc")


def _valid_correlation_id(value: str | None) -> str:
    if value and len(value) <= 128 and all(c.isalnum() or c in "-_." for c in value):
        return value
    return uuid.uuid4().hex


class RequestContextMiddleware:
    """Propagate ``X-Correlation-ID`` and add security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle an ASGI call."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers", [])).get(CORRELATION_HEADER.encode())
        request_id = _valid_correlation_id(incoming.decode("latin-1") if incoming else None)
        token = correlation_id.set(request_id)
        path: str = scope.get("path", "")
        csp = _DOCS_CSP if path.startswith(_DOCS_PATHS) else _STRICT_CSP

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[CORRELATION_HEADER] = request_id
                headers.setdefault("content-security-policy", csp)
                headers.setdefault("x-content-type-options", "nosniff")
                headers.setdefault("referrer-policy", "no-referrer")
                headers.setdefault("x-frame-options", "DENY")
                headers.setdefault("strict-transport-security", "max-age=31536000; includeSubDomains")
                headers.setdefault("cache-control", "no-store")
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            correlation_id.reset(token)


class ProtocolSwitchMiddleware:
    """Return ``503`` for MCP or A2A paths when the protocol is disabled in the settings."""

    def __init__(self, app: ASGIApp, *, is_enabled: Callable[[str], bool]) -> None:
        self.app = app
        self._is_enabled = is_enabled

    @staticmethod
    def protocol_for(path: str) -> str | None:
        """Return ``"mcp"``, ``"a2a"`` or ``None`` for a request path."""
        if path == "/mcp" or path.startswith("/mcp/"):
            return "mcp"
        if path.startswith("/a2a/") or path == "/a2a" or path.startswith("/.well-known/agent"):
            return "a2a"
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle an ASGI call."""
        protocol = self.protocol_for(scope.get("path", "")) if scope["type"] == "http" else None
        if protocol is None or self._is_enabled(protocol):
            await self.app(scope, receive, send)
            return
        body: dict[str, Any] = {
            "type": "https://dataplatform-mockup.dev/problems/protocol-disabled",
            "title": "Protocol disabled",
            "status": 503,
            "detail": f"The {protocol.upper()} endpoint is disabled in the platform settings.",
            "instance": scope.get("path", ""),
            "traceId": correlation_id.get(),
        }
        payload = json.dumps(body).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"content-type", b"application/problem+json"), (b"content-length", str(len(payload)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": payload})
