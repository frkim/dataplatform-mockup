"""Command-line interface: ``uv run dataplatform-client <command>``."""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from typing import Any

from dataplatform_client.a2a_client import PlatformA2AClient
from dataplatform_client.briefing import build_briefing
from dataplatform_client.mcp_client import PlatformError, PlatformMcpClient


def _table(columns: Sequence[str], rows: Sequence[dict[str, Any]]) -> str:
    cells = [[str(row.get(c, "")) for c in columns] for row in rows]
    widths = [max([len(c), *(len(r[i]) for r in cells)]) for i, c in enumerate(columns)]
    line = "  ".join(c.ljust(w) for c, w in zip(columns, widths, strict=True))
    out = [line, "  ".join("-" * w for w in widths)]
    out += ["  ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)) for r in cells]
    return "\n".join(out)


async def _tools(args: argparse.Namespace) -> str:
    async with PlatformMcpClient(args.base_url) as mcp:
        tools = await mcp.list_tools()
    return "\n".join(f"{name:16} {description}" for name, description in tools)


async def _sql(args: argparse.Namespace) -> str:
    async with PlatformMcpClient(args.base_url) as mcp:
        result = await mcp.run_sql(args.sql, max_rows=args.max_rows)
    if args.json:
        return json.dumps(result, indent=2)
    footer = f"\n({result['rowCount']} rows{', truncated' if result['truncated'] else ''}, {result['durationMs']} ms)"
    return _table([c["name"] for c in result["columns"]], result["rows"]) + footer


async def _ask(args: argparse.Namespace) -> str:
    async with PlatformMcpClient(args.base_url) as mcp:
        reply = await mcp.ask_agent(args.question, agent_id=args.agent)
    return json.dumps(reply, indent=2) if args.json else f"{reply['answer']}\n\nSQL:\n{reply.get('sql') or '-'}"


async def _agents(args: argparse.Namespace) -> str:
    async with PlatformMcpClient(args.base_url) as mcp:
        agents = await mcp.list_agents()
    a2a = PlatformA2AClient(args.base_url)
    lines = []
    for agent in agents:
        card = await a2a.get_card(agent["id"])
        skills = ", ".join(s.id for s in card.skills)
        lines.append(f"{agent['id']:20} {card.name} — {card.supported_interfaces[0].url}\n{'':20} skills: {skills}")
    return "\n".join(lines)


async def _a2a(args: argparse.Namespace) -> str:
    answer = await PlatformA2AClient(args.base_url).ask(args.agent, args.question)
    return json.dumps(answer.data, indent=2) if args.json else f"[{answer.agent} · {answer.state}]\n\n{answer.markdown}"


async def _briefing(args: argparse.Namespace) -> str:
    return await build_briefing(args.base_url)


def _leaf_exceptions(error: BaseException) -> list[BaseException]:
    if isinstance(error, BaseExceptionGroup):
        return [leaf for inner in error.exceptions for leaf in _leaf_exceptions(inner)]
    return [error]


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(prog="dataplatform-client", description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DATAPLATFORM_URL", "http://localhost:8000"),
        help="Platform base URL (env DATAPLATFORM_URL, default http://localhost:8000).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("tools", help="List the MCP tools.").set_defaults(handler=_tools)

    sql = sub.add_parser("sql", help="Run read-only SQL through MCP.")
    sql.add_argument("sql")
    sql.add_argument("--max-rows", type=int, default=50)
    sql.add_argument("--json", action="store_true")
    sql.set_defaults(handler=_sql)

    ask = sub.add_parser("ask", help="Ask an agent through the MCP ask_agent tool.")
    ask.add_argument("question")
    ask.add_argument("--agent", default="data-analyst")
    ask.add_argument("--json", action="store_true")
    ask.set_defaults(handler=_ask)

    sub.add_parser("agents", help="Resolve every A2A agent card.").set_defaults(handler=_agents)

    a2a = sub.add_parser("a2a", help="Send a message to an agent over A2A.")
    a2a.add_argument("agent")
    a2a.add_argument("question")
    a2a.add_argument("--json", action="store_true")
    a2a.set_defaults(handler=_a2a)

    sub.add_parser("briefing", help="Operations briefing combining MCP and A2A.").set_defaults(handler=_briefing)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = build_parser().parse_args(argv)
    exit_code = 0
    try:
        print(asyncio.run(args.handler(args)))
    except* PlatformError as group:  # MCP sessions surface errors inside anyio exception groups.
        for exc in _leaf_exceptions(group):
            print(f"error: {exc}", file=sys.stderr)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
