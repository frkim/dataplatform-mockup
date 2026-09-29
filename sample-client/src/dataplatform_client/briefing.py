"""Operations briefing: KPIs over MCP plus agent analysis over A2A, rendered as Markdown."""

from datetime import UTC, datetime
from typing import Any

from dataplatform_client.a2a_client import PlatformA2AClient
from dataplatform_client.mcp_client import PlatformMcpClient

KPI_SQL = """
SELECT
  (SELECT round(sum(total_amount), 2) FROM retail.sales.orders
    WHERE status <> 'cancelled' AND order_date >= DATE '2026-06-01') AS revenue_last_month,
  (SELECT count(*) FROM retail.sales.orders WHERE order_date >= DATE '2026-06-01') AS orders_last_month,
  (SELECT count(*) FROM manufacturing.production.machines WHERE status <> 'operational') AS machines_not_running,
  (SELECT count(*) FROM manufacturing.supply_chain.purchase_orders WHERE status = 'open') AS open_purchase_orders
"""

CHANNEL_SQL = """
SELECT channel, round(sum(total_amount), 2) AS revenue
FROM retail.sales.orders
WHERE status <> 'cancelled'
GROUP BY channel
ORDER BY revenue DESC
"""

AGENT_QUESTIONS = (
    ("supply-chain", "Which materials are below their reorder point?"),
    ("quality-maintenance", "Which machines need maintenance?"),
    ("sales-insights", "What are the top 5 products?"),
)


def _money(value: Any) -> str:
    return f"€{float(value):,.0f}"


def render_briefing(kpis: dict[str, Any], channels: list[dict[str, Any]], sections: list[tuple[str, str]]) -> str:
    """Render the briefing as Markdown."""
    lines = [
        "# Operations briefing",
        "",
        f"_Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC from the data platform (MCP + A2A)._",
        "",
        "## Key figures (via MCP `run_sql`)",
        "",
        "| KPI | Value |",
        "| --- | ---: |",
        f"| Revenue, June 2026 | {_money(kpis['revenue_last_month'])} |",
        f"| Orders, June 2026 | {kpis['orders_last_month']:,} |",
        f"| Machines degraded or down | {kpis['machines_not_running']} |",
        f"| Open purchase orders | {kpis['open_purchase_orders']:,} |",
        "",
        "### Revenue by channel",
        "",
    ]
    lines += [f"- {row['channel']}: {_money(row['revenue'])}" for row in channels]
    for title, markdown in sections:
        lines += ["", f"## {title} (via A2A)", "", markdown]
    return "\n".join(lines) + "\n"


async def build_briefing(base_url: str) -> str:
    """Collect KPIs over MCP, ask the specialist agents over A2A and render the report."""
    async with PlatformMcpClient(base_url) as mcp:
        kpis = (await mcp.run_sql(KPI_SQL))["rows"][0]
        channels = (await mcp.run_sql(CHANNEL_SQL))["rows"]
    a2a = PlatformA2AClient(base_url)
    sections = []
    for agent_id, question in AGENT_QUESTIONS:
        answer = await a2a.ask(agent_id, question)
        sections.append((answer.agent, f"> {question}\n\n{answer.markdown}"))
    return render_briefing(kpis, channels, sections)
