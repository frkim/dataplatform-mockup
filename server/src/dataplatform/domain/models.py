"""Domain and API models shared by the REST, MCP and A2A surfaces.

All models serialise to camelCase JSON (``pageSize``, ``rowCount``...) and accept both
camelCase and snake_case on input.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WarehouseSize = Literal["X-Small", "Small", "Medium", "Large", "X-Large"]
QuerySource = Literal["ui", "api", "mcp", "a2a", "agent"]
QueryStatus = Literal["succeeded", "failed"]


def to_camel(name: str) -> str:
    """``row_count`` -> ``rowCount``; unlike pydantic's helper, ``a2a_enabled`` -> ``a2aEnabled``."""
    first, *rest = name.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


class ApiModel(BaseModel):
    """Base model: camelCase aliases, snake_case attribute names."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Page[T](ApiModel):
    """A page of a collection."""

    items: list[T]
    total: int
    page: int
    page_size: int


class Catalog(ApiModel):
    """Top-level namespace, equivalent to a Snowflake database or a Unity Catalog catalog."""

    name: str
    description: str
    schema_count: int


class Schema(ApiModel):
    """Second-level namespace inside a catalog."""

    catalog: str
    name: str
    description: str
    table_count: int


class Column(ApiModel):
    """A table column."""

    name: str
    type: str
    description: str
    nullable: bool
    primary_key: bool = False


class TableSummary(ApiModel):
    """A table with its row count."""

    catalog: str
    schema_name: str = Field(alias="schema")
    name: str
    full_name: str
    description: str
    row_count: int
    column_count: int


class TableDetail(TableSummary):
    """A table with its columns."""

    columns: list[Column]


class ResultColumn(ApiModel):
    """A column of a query result."""

    name: str
    type: str


class QueryRequest(ApiModel):
    """A SQL statement to execute."""

    sql: str = Field(min_length=1, max_length=20_000)
    max_rows: int | None = Field(default=None, ge=1, le=10_000)


class QueryResult(ApiModel):
    """The tabular result of a query."""

    query_id: str
    columns: list[ResultColumn]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    duration_ms: float


class QueryHistoryEntry(ApiModel):
    """An executed query, successful or not."""

    id: str
    sql: str
    source: QuerySource
    status: QueryStatus
    row_count: int
    duration_ms: float
    error: str | None = None
    started_at: datetime


class AgentSkillInfo(ApiModel):
    """A capability advertised by an agent."""

    id: str
    name: str
    description: str
    examples: list[str]


class AgentInfo(ApiModel):
    """An AI agent hosted by the platform."""

    id: str
    name: str
    description: str
    domain: str
    enabled: bool
    skills: list[AgentSkillInfo]
    a2a_card_url: str


class AgentRequest(ApiModel):
    """A natural-language message sent to an agent."""

    message: str = Field(min_length=1, max_length=2_000)


class AgentReply(ApiModel):
    """An agent answer, with the SQL it ran and the resulting rows."""

    agent_id: str
    skill_id: str
    answer: str
    sql: str | None = None
    columns: list[ResultColumn] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class PlatformSettings(ApiModel):
    """Runtime-configurable platform settings."""

    workspace_name: str = Field(default="Contoso Data Platform", min_length=1, max_length=80)
    warehouse_size: WarehouseSize = "X-Small"
    default_page_size: int = Field(default=25, ge=1, le=100)
    max_query_rows: int = Field(default=1_000, ge=1, le=10_000)
    simulated_latency_ms: int = Field(default=0, ge=0, le=5_000)
    mcp_enabled: bool = True
    a2a_enabled: bool = True
    agents_enabled: dict[str, bool] = Field(default_factory=dict)


class PlatformEndpoints(ApiModel):
    """Absolute URLs of the platform surfaces."""

    rest: str
    mcp: str
    a2a: str
    openapi: str


class PlatformStats(ApiModel):
    """Aggregate counts over the catalog."""

    catalogs: int
    schemas: int
    tables: int
    total_rows: int


class PlatformInfo(ApiModel):
    """Platform identity, endpoints and statistics."""

    name: str
    version: str
    workspace_name: str
    warehouse_size: WarehouseSize
    engine: str
    endpoints: PlatformEndpoints
    stats: PlatformStats
