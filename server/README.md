# Data platform server

FastAPI service that loads synthetic manufacturing and retail data into a sandboxed in-memory
[DuckDB](https://duckdb.org) engine and serves it through three surfaces on one port:

| Surface | Path | Consumers |
| --- | --- | --- |
| REST API v1 | `/api/v1/*` (OpenAPI at `/docs`) | Web console, scripts |
| MCP (Streamable HTTP, stateless) | `/mcp` | AI assistants (VS Code, Claude Desktop…), sample client |
| A2A 1.0 (JSON-RPC) | `/a2a/{agentId}`, cards at `/a2a/{agentId}/.well-known/agent-card.json` | Other agents, sample client |

Health probes: `/health/live`, `/health/ready`.

## Layout

```text
src/dataplatform/
├── api/              # FastAPI routes, dependencies, middleware, problem+json errors
├── protocols/        # MCP server and A2A executors/cards
├── services/         # catalog, query, agent, settings services (shared by every surface)
├── agents/           # rule-based agents: data-analyst (router) + 3 specialists
├── domain/           # API models and domain errors
├── infrastructure/   # DuckDB engine sandbox, catalog metadata, sample-data generator
├── config.py         # DATAPLATFORM_* environment configuration
├── container.py      # composition root
└── main.py           # `uv run dataplatform` entry point
```

## Run

```bash
uv sync
uv run dataplatform            # http://localhost:8000 (docs at /docs)
```

Configuration is read from `DATAPLATFORM_*` environment variables or a `.env` file; see
[`.env.example`](.env.example).

## Quality gates

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest                  # coverage gate: 80 %
```

## Try it

```bash
curl -s localhost:8000/api/v1/catalogs | jq
curl -s -X POST localhost:8000/api/v1/query -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT channel, round(sum(total_amount)) AS revenue FROM retail.sales.orders GROUP BY channel"}' | jq
curl -s -X POST localhost:8000/api/v1/agents/data-analyst/invoke -H 'Content-Type: application/json' \
  -d '{"message":"Which materials are below their reorder point?"}' | jq -r .answer
```

Add the MCP server to VS Code (`.vscode/mcp.json`):

```json
{ "servers": { "dataplatform": { "type": "http", "url": "http://localhost:8000/mcp" } } }
```
