"""REST API v1 routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, Path, status
from fastapi.concurrency import run_in_threadpool

from dataplatform import __version__
from dataplatform.api.deps import ContainerDep, ListOptionsDep
from dataplatform.domain.models import (
    AgentInfo,
    AgentReply,
    AgentRequest,
    Catalog,
    Page,
    PlatformEndpoints,
    PlatformInfo,
    PlatformSettings,
    QueryHistoryEntry,
    QueryRequest,
    QueryResult,
    QuerySource,
    Schema,
    TableDetail,
    TableSummary,
)

router = APIRouter(prefix="/api/v1")

Identifier = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
AgentId = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")]
_PROBLEM = {"content": {"application/problem+json": {}}}
_ERRORS: dict[int | str, dict[str, Any]] = {400: _PROBLEM, 404: _PROBLEM}


@router.get("/platform", response_model=PlatformInfo, tags=["platform"], summary="Platform identity and endpoints")
def get_platform(container: ContainerDep) -> PlatformInfo:
    """Return the platform name, version, endpoint URLs and catalog statistics."""
    settings = container.settings.get()
    base = container.config.public_base_url
    return PlatformInfo(
        name="Data Platform Mockup",
        version=__version__,
        workspace_name=settings.workspace_name,
        warehouse_size=settings.warehouse_size,
        engine=f"DuckDB {container.engine.version}",
        endpoints=PlatformEndpoints(rest=f"{base}/api/v1", mcp=f"{base}/mcp", a2a=f"{base}/a2a", openapi=f"{base}/openapi.json"),
        stats=container.catalog.stats(),
    )


@router.get("/catalogs", response_model=Page[Catalog], tags=["catalog"], responses=_ERRORS)
def list_catalogs(container: ContainerDep, options: ListOptionsDep) -> Page[Catalog]:
    """List catalogs (sortable/filterable on name, description, schemaCount)."""
    return container.catalog.list_catalogs(options)


@router.get("/catalogs/{catalog}/schemas", response_model=Page[Schema], tags=["catalog"], responses=_ERRORS)
def list_schemas(catalog: Identifier, container: ContainerDep, options: ListOptionsDep) -> Page[Schema]:
    """List the schemas of a catalog."""
    return container.catalog.list_schemas(catalog, options)


@router.get(
    "/catalogs/{catalog}/schemas/{schema}/tables", response_model=Page[TableSummary], tags=["catalog"], responses=_ERRORS
)
def list_tables(catalog: Identifier, schema: Identifier, container: ContainerDep, options: ListOptionsDep) -> Page[TableSummary]:
    """List the tables of a schema."""
    return container.catalog.list_tables(catalog, schema, options)


@router.get(
    "/catalogs/{catalog}/schemas/{schema}/tables/{table}", response_model=TableDetail, tags=["catalog"], responses=_ERRORS
)
def get_table(catalog: Identifier, schema: Identifier, table: Identifier, container: ContainerDep) -> TableDetail:
    """Describe a table and its columns."""
    return container.catalog.get_table(catalog, schema, table)


@router.get(
    "/catalogs/{catalog}/schemas/{schema}/tables/{table}/rows",
    response_model=Page[dict[str, Any]],
    tags=["catalog"],
    responses=_ERRORS,
    summary="Browse table rows",
)
def get_rows(
    catalog: Identifier, schema: Identifier, table: Identifier, container: ContainerDep, options: ListOptionsDep
) -> Page[dict[str, Any]]:
    """Page through table rows.

    Supports ``sort``/``order`` on any column, ``q`` (case-insensitive search across text columns) and
    ``filter[column]=value`` or ``filter[column][op]=value`` with op in contains, equals, startsWith,
    endsWith, eq, neq, gt, gte, lt, lte, isEmpty, isNotEmpty.
    """
    return container.catalog.query_rows(catalog, schema, table, options)


@router.post("/query", response_model=QueryResult, tags=["query"], responses=_ERRORS, summary="Run a read-only SQL query")
def run_query(
    body: QueryRequest,
    container: ContainerDep,
    x_query_source: Annotated[QuerySource | None, Header(alias="X-Query-Source")] = None,
) -> QueryResult:
    """Execute one read-only ``SELECT`` statement using three-part names (``retail.sales.orders``)."""
    return container.queries.run(body.sql, source=x_query_source or "api", max_rows=body.max_rows)


@router.get("/queries", response_model=Page[QueryHistoryEntry], tags=["query"], responses=_ERRORS)
def list_queries(container: ContainerDep, options: ListOptionsDep) -> Page[QueryHistoryEntry]:
    """Query history, most recent first by default."""
    return container.queries.history.list(options)


@router.get("/agents", response_model=Page[AgentInfo], tags=["agents"], responses=_ERRORS)
def list_agents(container: ContainerDep, options: ListOptionsDep) -> Page[AgentInfo]:
    """List the AI agents hosted by the platform."""
    return container.agents.list(options)


@router.get("/agents/{agent_id}", response_model=AgentInfo, tags=["agents"], responses=_ERRORS)
def get_agent(agent_id: AgentId, container: ContainerDep) -> AgentInfo:
    """Describe an agent and its skills."""
    return container.agents.info(agent_id)


@router.post(
    "/agents/{agent_id}/invoke",
    response_model=AgentReply,
    tags=["agents"],
    responses={**_ERRORS, 409: _PROBLEM},
    summary="Ask an agent a question",
)
async def invoke_agent(agent_id: AgentId, body: AgentRequest, container: ContainerDep) -> AgentReply:
    """Send a natural-language message to an agent. Returns ``409`` when the agent is disabled."""
    return await run_in_threadpool(container.agents.invoke, agent_id, body.message, source="agent")


@router.get("/settings", response_model=PlatformSettings, tags=["settings"])
def get_settings(container: ContainerDep) -> PlatformSettings:
    """Return the runtime settings."""
    return container.settings.get()


@router.put("/settings", response_model=PlatformSettings, tags=["settings"], responses=_ERRORS, status_code=status.HTTP_200_OK)
def put_settings(body: PlatformSettings, container: ContainerDep) -> PlatformSettings:
    """Replace the runtime settings (in memory; reset on restart)."""
    return container.settings.update(body)
