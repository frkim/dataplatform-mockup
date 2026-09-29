"""FastAPI application factory: REST API, MCP and A2A on a single ASGI app."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from dataplatform import __version__
from dataplatform.api.errors import install_error_handlers
from dataplatform.api.middleware import CORRELATION_HEADER, ProtocolSwitchMiddleware, RequestContextMiddleware
from dataplatform.api.routes import health, v1
from dataplatform.config import AppConfig, get_config
from dataplatform.container import Container, build_container
from dataplatform.logging_config import configure_logging
from dataplatform.protocols.a2a_server import mount_a2a
from dataplatform.protocols.mcp_server import create_mcp_server

logger = logging.getLogger(__name__)

DESCRIPTION = """\
Mock enterprise data platform (Snowflake / Databricks style) with synthetic **manufacturing** and
**retail** data and rule-based AI agents.

* **REST** — this API (`/api/v1`), used by the web console.
* **MCP** — Streamable HTTP endpoint at `/mcp` for AI assistants.
* **A2A** — one Agent2Agent endpoint per agent at `/a2a/{agentId}`
  (cards at `/a2a/{agentId}/.well-known/agent-card.json`).
"""


def create_app(config: AppConfig | None = None, container: Container | None = None) -> FastAPI:
    """Build the application. Loads the sample data eagerly so a misconfiguration fails fast."""
    config = config or get_config()
    configure_logging(config.log_level)
    container = container or build_container(config)

    mcp = create_mcp_server(container)
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=config.mcp_allowed_hosts,
            allowed_origins=config.mcp_allowed_origins,
        ),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            logger.info("platform started", extra={"event": "app.started", "baseUrl": config.public_base_url})
            yield
        logger.info("platform stopped", extra={"event": "app.stopped"})

    app = FastAPI(
        title="Data Platform Mockup",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "platform", "description": "Platform identity and discovery."},
            {"name": "catalog", "description": "Catalogs, schemas, tables and rows."},
            {"name": "query", "description": "Read-only SQL and query history."},
            {"name": "agents", "description": "AI agents (also reachable through MCP and A2A)."},
            {"name": "settings", "description": "Runtime settings."},
            {"name": "health", "description": "Liveness and readiness probes."},
        ],
    )
    app.state.container = container
    install_error_handlers(app)

    app.include_router(health.router)
    app.include_router(v1.router)
    app.router.routes.extend(mcp_app.routes)
    mount_a2a(app, container)

    settings = container.settings

    def protocol_enabled(protocol: str) -> bool:
        current = settings.get()
        return current.mcp_enabled if protocol == "mcp" else current.a2a_enabled

    # Starlette runs the last-added middleware first: context → CORS → protocol switch → app.
    app.add_middleware(ProtocolSwitchMiddleware, is_enabled=protocol_enabled)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allowed_origins,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Query-Source", "X-Correlation-ID"],
        expose_headers=[CORRELATION_HEADER],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)
    return app
