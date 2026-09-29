# AGENTS.md

This is the contract every AI coding agent (GitHub Copilot coding agent, Copilot CLI, Copilot in the IDE, and
others) reads before working in this repository. It follows the
[ai-coding-standards](https://github.com/frkim/ai-coding-standards) template.

## Project overview

A mock data platform, like Snowflake or Databricks, for prototyping AI applications. A FastAPI server loads
deterministic manufacturing and retail sample data into a sandboxed in-memory DuckDB engine. It serves the data
and four rule-based AI agents over REST (`/api/v1`), MCP (`/mcp`) and A2A (`/a2a/{agent}`). A Next.js console
browses the data and configures settings. A Python sample client consumes the platform over MCP and A2A.
Runs locally or with Docker Compose; the Azure target is Container Apps.

- **Frontend**: Next.js (App Router, TypeScript) with Material UI and MUI DataGrid; charts with D3.js
- **Backend**: Python 3.12 FastAPI, MCP Python SDK, A2A Python SDK
- **Data**: DuckDB in-memory, generated at start-up (no external database)
- **Hosting**: Azure Container Apps (planned); Docker Compose locally

## Setup

```bash
# prerequisites: Python 3.12 + uv, Node.js 24 LTS + npm, optionally Docker
cd server && uv sync
cd sample-client && uv sync
cd web && npm ci
```

Configure the Microsoft-protected package feed on managed devices before the first sync — see
`standards/development/package-feeds.md` in the ai-coding-standards repository:

- PyPI: `https://packagefeedproxy.microsoft.io/pypi/simple` (`export UV_INDEX_URL=...`)

## Commands

| Task | Command |
| --- | --- |
| Run server | `cd server && uv run dataplatform` (http://localhost:8000, docs at `/docs`) |
| Run web console | `cd web && npm run dev` (http://localhost:3000) |
| Run sample client | `cd sample-client && uv run dataplatform-client briefing` |
| Lint (Python) | `uv run ruff check . && uv run ruff format --check .` (in `server/` or `sample-client/`) |
| Type-check (Python) | `uv run mypy src tests` |
| Test (Python) | `uv run pytest` (coverage gate 80 %) |
| Lint / type-check / test (web) | `npm run lint && npm run format:check && npm run typecheck && npm test` |
| Build (web) | `npm run build` |
| Full stack | `docker compose up --build` |

## Project structure

```text
server/src/dataplatform/   api/ (REST) · protocols/ (MCP, A2A) · services/ · agents/ · domain/ · infrastructure/
server/tests/              pytest suite (functions named should_*)
web/src/                   app/ (pages) · components/ · lib/ (API client, theme, formatting)
sample-client/src/         MCP client, A2A client, briefing, CLI
docs/adr/                  architecture decision records
tmp/scripts/               throwaway agent/developer scripts (git-ignored)
```

## Standards to follow

- Coding: `instructions/coding-standards.instructions.md`
- Security: `instructions/security.instructions.md`
- Testing: `instructions/testing.instructions.md`
- Documentation: `instructions/documentation.instructions.md`
- Architecture and UI: `instructions/architecture.instructions.md`

## Non-negotiables

- Never commit secrets or connection strings; use managed identities for Azure access.
- Every UI has a **dark/light mode toggle** that respects the OS preference and persists the user's choice.
- Every data table supports **sorting and filtering on column headers**, **pagination**, and a **global search
  box**. Large data sets are sorted, filtered and paged on the server.
- Validate all input; paginate every collection endpoint; errors are RFC 9457 `application/problem+json`.
- SQL from users stays **read-only** through `Engine.execute`. Never add a code path that runs user SQL on the
  raw DuckDB connection.
- REST, MCP and A2A go through the **same services**. Add behaviour in `services/` or `agents/`, then expose it,
  instead of duplicating logic in a protocol adapter.
- Before adding a library, SDK, or runtime, research its current stable version online and use that version.
- Diagrams are Mermaid, interactive visualisations use D3.js, and presentations are Marp Markdown.
- When you implement a feature, test it: run the tests and exercise the feature, then report what you observed.
- Update documentation in the same pull request as the code.

## Pull requests

- Conventional Commit titles (`feat:`, `fix:`, `docs:`, ...), squash merge.
- Describe what changed, why, and how it was verified.
- CI (lint, build, test, CodeQL) must be green before merge.

## Gotchas

- The root `.gitignore` is the Python template: it ignores `lib/`. `web/src/lib/` is re-included with a negation.
  Keep that line.
- MCP DNS-rebinding protection only allows `localhost` hosts by default. When the server is reached under another
  host name, set `DATAPLATFORM_MCP_ALLOWED_HOSTS` / `DATAPLATFORM_MCP_ALLOWED_ORIGINS`.
- A2A agent cards advertise `DATAPLATFORM_PUBLIC_BASE_URL`, and clients follow that URL, so set it to the
  externally reachable address.
- MCP client errors arrive wrapped in nested `ExceptionGroup`s (anyio task groups); the sample client unwraps
  them with `except*`.
- Sample data is regenerated from `DATAPLATFORM_DATA_SEED` on every start, and settings live in memory. Tests
  that change settings must reset them.
- Agents inline literals into the SQL they show to users. Those values come only from fixed vocabularies,
  numbers and catalog metadata, never from raw user text.
