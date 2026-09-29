"""The sample client against a live platform: MCP, A2A, the briefing scenario and the CLI."""

import json

import pytest
from dataplatform.domain.models import PlatformSettings

from dataplatform_client.a2a_client import PlatformA2AClient
from dataplatform_client.briefing import build_briefing
from dataplatform_client.cli import main
from dataplatform_client.mcp_client import PlatformError, PlatformMcpClient
from tests.conftest import Platform


async def should_discover_tools_when_connected_over_mcp(platform: Platform) -> None:
    # Act
    async with PlatformMcpClient(platform.base_url) as mcp:
        tools = dict(await mcp.list_tools())

    # Assert
    assert {"run_sql", "ask_agent", "list_tables"} <= set(tools)


async def should_return_rows_when_running_sql_over_mcp(platform: Platform) -> None:
    # Act
    async with PlatformMcpClient(platform.base_url) as mcp:
        result = await mcp.run_sql("SELECT count(*) AS plants FROM manufacturing.production.plants")

    # Assert
    assert result["rows"] == [{"plants": 4}]


async def should_raise_platform_error_when_sql_writes_over_mcp(platform: Platform) -> None:
    # Act / Assert
    with pytest.raises(ExceptionGroup) as caught:
        async with PlatformMcpClient(platform.base_url) as mcp:
            await mcp.run_sql("DELETE FROM retail.sales.orders")
    assert caught.group_contains(PlatformError)


async def should_list_agents_with_card_urls_over_mcp(platform: Platform) -> None:
    # Act
    async with PlatformMcpClient(platform.base_url) as mcp:
        agents = await mcp.list_agents()

    # Assert
    assert {a["a2aCardUrl"] for a in agents} == {
        f"{platform.base_url}/a2a/{a['id']}/.well-known/agent-card.json" for a in agents
    }


async def should_resolve_card_when_agent_published_over_a2a(platform: Platform) -> None:
    # Act
    card = await PlatformA2AClient(platform.base_url).get_card("sales-insights")

    # Assert
    assert card.name == "Sales Insights Agent"
    assert card.supported_interfaces[0].url == f"{platform.base_url}/a2a/sales-insights"


async def should_return_markdown_and_data_when_asking_over_a2a(platform: Platform) -> None:
    # Act
    answer = await PlatformA2AClient(platform.base_url).ask("sales-insights", "What is the revenue split by channel?")

    # Assert
    assert answer.state == "TASK_STATE_COMPLETED"
    assert "revenue" in answer.markdown.lower()
    assert answer.data["skillId"] == "channel-mix"
    assert answer.data["rows"]


async def should_raise_platform_error_when_agent_disabled_over_a2a(platform: Platform) -> None:
    # Arrange
    platform.container.settings.update(PlatformSettings(agents_enabled={"supply-chain": False}))

    # Act / Assert
    with pytest.raises(PlatformError, match="TASK_STATE_FAILED"):
        await PlatformA2AClient(platform.base_url).ask("supply-chain", "open purchase orders")


async def should_combine_mcp_and_a2a_when_building_briefing(platform: Platform) -> None:
    # Act
    report = await build_briefing(platform.base_url)

    # Assert
    assert report.startswith("# Operations briefing")
    assert "| Revenue, June 2026 | €" in report
    assert "## Supply Chain Agent (via A2A)" in report
    assert "## Quality & Maintenance Agent (via A2A)" in report
    assert "## Sales Insights Agent (via A2A)" in report


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["tools"], "run_sql"),
        (["sql", "SELECT 42 AS answer"], "answer"),
        (["ask", "How many customers do we have?"], "3,000"),
        (["agents"], "quality-maintenance"),
        (["a2a", "quality-maintenance", "What is the production yield per plant?"], "TASK_STATE_COMPLETED"),
    ],
)
def should_print_result_when_cli_command_succeeds(
    platform: Platform, capsys: pytest.CaptureFixture[str], args: list[str], expected: str
) -> None:
    # Act
    code = main(["--base-url", platform.base_url, *args])

    # Assert
    assert code == 0
    assert expected in capsys.readouterr().out


@pytest.mark.parametrize(
    "args",
    [
        ["sql", "SELECT 1 AS one", "--json"],
        ["ask", "top 3 products", "--json"],
        ["a2a", "sales-insights", "top 3 products", "--json"],
    ],
)
def should_print_json_when_json_flag_given(
    platform: Platform, capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    # Act
    code = main(["--base-url", platform.base_url, *args])

    # Assert
    assert code == 0
    assert isinstance(json.loads(capsys.readouterr().out), dict)


def should_exit_with_error_when_platform_rejects_request(
    platform: Platform, capsys: pytest.CaptureFixture[str]
) -> None:
    # Act
    code = main(["--base-url", platform.base_url, "sql", "DROP TABLE retail.sales.orders"])

    # Assert
    assert code == 1
    assert "read-only" in capsys.readouterr().err
