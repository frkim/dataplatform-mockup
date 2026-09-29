"""MCP tools, resources and prompts, exercised in-process through the MCP client."""

from typing import Any

import pytest
from mcp import Client
from mcp.types import TextContent, TextResourceContents

from dataplatform.container import Container
from dataplatform.protocols.mcp_server import create_mcp_server


@pytest.fixture
def mcp_client(container: Container) -> Client:
    return Client(create_mcp_server(container))


def _text(content: object) -> str:
    assert isinstance(content, TextContent | TextResourceContents)
    return content.text


async def _call(client: Client, tool: str, args: dict[str, Any]) -> Any:
    async with client:
        return await client.call_tool(tool, args)


async def should_list_platform_tools_when_connected(mcp_client: Client) -> None:
    # Act
    async with mcp_client:
        tools = await mcp_client.list_tools()

    # Assert
    names = {t.name for t in tools.tools}
    assert names == {"list_tables", "describe_table", "preview_table", "run_sql", "list_agents", "ask_agent"}
    assert all(t.annotations and t.annotations.read_only_hint for t in tools.tools)


async def should_return_structured_rows_when_running_sql(mcp_client: Client) -> None:
    # Act
    result = await _call(mcp_client, "run_sql", {"sql": "SELECT count(*) AS n FROM retail.sales.stores"})

    # Assert
    assert not result.is_error
    assert result.structured_content["rows"] == [{"n": 18}]


async def should_return_tool_error_when_sql_writes(mcp_client: Client) -> None:
    # Act
    result = await _call(mcp_client, "run_sql", {"sql": "DROP TABLE retail.sales.stores"})

    # Assert
    assert result.is_error
    assert "read-only" in _text(result.content[0])


async def should_filter_tables_when_catalog_given(mcp_client: Client) -> None:
    # Act
    result = await _call(mcp_client, "list_tables", {"catalog": "manufacturing"})

    # Assert
    tables = result.structured_content["result"]
    assert len(tables) == 10
    assert all(t["fullName"].startswith("manufacturing.") for t in tables)


async def should_describe_and_preview_when_table_exists(mcp_client: Client) -> None:
    # Act
    async with mcp_client:
        described = await mcp_client.call_tool("describe_table", {"table": "retail.sales.products"})
        preview = await mcp_client.call_tool("preview_table", {"table": "retail.sales.products", "limit": 3})
        missing = await mcp_client.call_tool("describe_table", {"table": "retail.sales.nope"})

    # Assert
    assert any(c["name"] == "unit_price" for c in described.structured_content["columns"])
    assert preview.structured_content["rowCount"] == 3
    assert missing.is_error


async def should_route_question_when_asking_agent(mcp_client: Client) -> None:
    # Act
    async with mcp_client:
        agents = await mcp_client.call_tool("list_agents", {})
        answer = await mcp_client.call_tool("ask_agent", {"question": "What is the revenue split by channel?"})

    # Assert
    assert len(agents.structured_content["result"]) == 4
    assert answer.structured_content["skillId"] == "sales-insights/channel-mix"


async def should_expose_schema_resource_and_prompt_when_requested(mcp_client: Client) -> None:
    # Act
    async with mcp_client:
        overview = await mcp_client.read_resource("dataplatform://catalog")
        schema = await mcp_client.read_resource("dataplatform://tables/retail/sales/orders")
        prompt = await mcp_client.get_prompt("analyze-table", {"table": "retail.sales.orders"})

    # Assert
    assert "retail.sales.orders" in _text(overview.contents[0])
    assert "| order_id |" in _text(schema.contents[0])
    assert "describe_table" in _text(prompt.messages[0].content)
