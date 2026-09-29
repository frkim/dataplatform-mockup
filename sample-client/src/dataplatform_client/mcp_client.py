"""MCP access to the platform: a thin typed wrapper around the MCP SDK client."""

from types import TracebackType
from typing import Any, Self

from mcp import Client
from mcp.types import CallToolResult, TextContent


class PlatformError(RuntimeError):
    """The platform rejected a request (tool error, failed task...)."""


def _tool_payload(tool: str, result: CallToolResult) -> Any:
    if result.is_error:
        message = " ".join(c.text for c in result.content if isinstance(c, TextContent))
        raise PlatformError(f"{tool}: {message}")
    payload = result.structured_content or {}
    # Tools returning lists are wrapped as {"result": [...]} by MCP structured output.
    return payload.get("result", payload) if set(payload) == {"result"} else payload


class PlatformMcpClient:
    """Connects to ``{base_url}/mcp`` (Streamable HTTP) and calls the platform tools."""

    def __init__(self, base_url: str) -> None:
        """Prepare a client for the platform at ``base_url``."""
        self._client = Client(f"{base_url.rstrip('/')}/mcp")

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self._client.__aexit__(exc_type, exc, tb)

    async def list_tools(self) -> list[tuple[str, str]]:
        """Return ``(name, description)`` for every tool the platform exposes."""
        result = await self._client.list_tools()
        return [(t.name, (t.description or "").strip().splitlines()[0]) for t in result.tools]

    async def call(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call a tool and return its structured content.

        Raises:
            PlatformError: The tool reported an error.

        """
        return _tool_payload(tool, await self._client.call_tool(tool, arguments or {}))

    async def run_sql(self, sql: str, max_rows: int = 100) -> dict[str, Any]:
        """Run a read-only SQL query; returns ``columns``, ``rows``, ``rowCount``, ``truncated``..."""
        result: dict[str, Any] = await self.call("run_sql", {"sql": sql, "max_rows": max_rows})
        return result

    async def ask_agent(self, question: str, agent_id: str = "data-analyst") -> dict[str, Any]:
        """Ask a platform agent through the MCP ``ask_agent`` tool."""
        result: dict[str, Any] = await self.call("ask_agent", {"question": question, "agent_id": agent_id})
        return result

    async def list_agents(self) -> list[dict[str, Any]]:
        """Return the platform agents, including their A2A card URL (``a2aCardUrl``)."""
        result: list[dict[str, Any]] = await self.call("list_agents")
        return result
