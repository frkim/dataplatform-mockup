"""MCP server (Model Context Protocol, Streamable HTTP) exposing the platform to AI assistants.

Tools let an MCP host (VS Code, Claude Desktop, Copilot...) explore the catalog, run read-only
SQL and ask the platform agents questions. Resources expose table schemas; a prompt template
bootstraps a table analysis.
"""

from collections.abc import Callable
from typing import Annotated, Any

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver import UserMessage
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from dataplatform import __version__
from dataplatform.container import Container
from dataplatform.domain.errors import DomainError, NotFoundError

INSTRUCTIONS = """\
This server is a mock enterprise data platform (like Snowflake or Databricks) with synthetic
manufacturing and retail data. Tables use three-part names: catalog.schema.table
(e.g. retail.sales.orders). Start with list_tables, inspect a table with describe_table, then use
run_sql for read-only DuckDB SQL, or ask_agent to let a domain agent answer in natural language."""

_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


async def _call[T](fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking service call in a worker thread, mapping domain errors to tool errors."""
    try:
        return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))
    except DomainError as exc:
        raise ToolError(exc.detail) from exc


def create_mcp_server(container: Container) -> MCPServer:
    """Build the MCP server bound to the application services."""
    mcp: MCPServer = MCPServer(
        name="dataplatform-mockup",
        title="Data Platform Mockup",
        description="Mock Snowflake/Databricks-like data platform with manufacturing and retail data and AI agents.",
        instructions=INSTRUCTIONS,
        version=__version__,
    )

    @mcp.tool(title="List tables", annotations=_READ_ONLY)
    async def list_tables(
        catalog: Annotated[str | None, Field(description="Optional catalog filter: manufacturing or retail.")] = None,
    ) -> list[dict[str, Any]]:
        """List every table (catalog.schema.table) with its description and row count."""
        tables = await _call(container.catalog.all_table_summaries)
        return [
            {"fullName": t.full_name, "description": t.description, "rowCount": t.row_count}
            for t in tables
            if catalog is None or t.catalog == catalog
        ]

    @mcp.tool(title="Describe table", annotations=_READ_ONLY)
    async def describe_table(
        table: Annotated[str, Field(description="Three-part table name, e.g. retail.sales.orders.")],
    ) -> dict[str, Any]:
        """Return the columns (name, type, description) of a table."""
        definition = await _call(container.catalog.resolve, table)
        detail = await _call(container.catalog.get_table, definition.catalog, definition.schema, definition.name)
        return detail.model_dump(by_alias=True)

    @mcp.tool(title="Preview table", annotations=_READ_ONLY)
    async def preview_table(
        table: Annotated[str, Field(description="Three-part table name, e.g. manufacturing.production.machines.")],
        limit: Annotated[int, Field(ge=1, le=100, description="Number of rows (1-100).")] = 10,
    ) -> dict[str, Any]:
        """Return the first rows of a table."""
        definition = await _call(container.catalog.resolve, table)
        result = await _call(
            container.queries.run,
            f"SELECT * FROM {definition.quoted_name} LIMIT {int(limit)}",  # noqa: S608 - allowlisted identifier, int
            source="mcp",
        )
        return result.model_dump(by_alias=True)

    @mcp.tool(title="Run SQL", annotations=_READ_ONLY)
    async def run_sql(
        sql: Annotated[
            str, Field(min_length=1, max_length=20_000, description="One read-only DuckDB SELECT statement.")
        ],
        max_rows: Annotated[int, Field(ge=1, le=1_000, description="Maximum rows to return.")] = 100,
    ) -> dict[str, Any]:
        """Execute a read-only SQL SELECT with three-part table names and return columns and rows."""
        result = await _call(container.queries.run, sql, source="mcp", max_rows=max_rows)
        return result.model_dump(by_alias=True)

    @mcp.tool(title="List agents", annotations=_READ_ONLY)
    async def list_agents() -> list[dict[str, Any]]:
        """List the platform AI agents, their skills and example questions."""
        agents = await _call(container.agents.all_info)
        return [a.model_dump(by_alias=True) for a in agents]

    @mcp.tool(title="Ask agent", annotations=_READ_ONLY)
    async def ask_agent(
        question: Annotated[str, Field(min_length=1, max_length=2_000, description="Natural-language question.")],
        agent_id: Annotated[
            str,
            Field(
                description=(
                    "data-analyst (default, routes to specialists), sales-insights, supply-chain "
                    "or quality-maintenance."
                )
            ),
        ] = "data-analyst",
    ) -> dict[str, Any]:
        """Ask a platform agent a business question; returns a Markdown answer, the SQL it ran and the rows."""
        answer = await _call(container.agents.invoke, agent_id, question, source="mcp")
        return answer.model_dump(by_alias=True)

    @mcp.resource(
        "dataplatform://tables/{catalog}/{schema}/{table}",
        name="table-schema",
        title="Table schema",
        description="Column definitions of a table, as Markdown.",
        mime_type="text/markdown",
    )
    def table_schema(catalog: str, schema: str, table: str) -> str:
        try:
            detail = container.catalog.get_table(catalog, schema, table)
        except NotFoundError as exc:
            raise ResourceNotFoundError(exc.detail) from exc
        lines = [
            f"# {detail.full_name}",
            "",
            detail.description,
            "",
            "| Column | Type | Description |",
            "| --- | --- | --- |",
        ]
        lines += [f"| {c.name} | {c.type} | {c.description} |" for c in detail.columns]
        return "\n".join(lines)

    @mcp.resource(
        "dataplatform://catalog",
        name="catalog",
        title="Catalog overview",
        description="Every table of the platform with its description and row count.",
        mime_type="text/markdown",
    )
    def catalog_overview() -> str:
        lines = ["# Data Platform Mockup catalog", ""]
        lines += [
            f"- `{t.full_name}` — {t.description} ({t.row_count:,} rows)"
            for t in container.catalog.all_table_summaries()
        ]
        return "\n".join(lines)

    @mcp.prompt(name="analyze-table", title="Analyze a table", description="Explore a table and summarise insights.")
    def analyze_table(table: str) -> list[UserMessage]:
        return [
            UserMessage(
                f"Analyse the table {table} on the data platform. First call describe_table, then preview_table, "
                "then write two or three run_sql aggregations that reveal interesting patterns, and summarise the "
                "findings with the SQL you used."
            )
        ]

    return mcp
