# ADR-0003: Expose MCP and A2A with the official SDKs on the REST server

- Status: Accepted
- Date: 2026-09-29

## Context

Consumers include AI assistants (VS Code, Claude), which speak MCP, and other agents, which speak A2A. The
issue asks for an "MCP + A2A server". Hand-written protocol handling would drift from the specifications.

## Decision

- Use the official **MCP Python SDK** (`mcp` 2.x) in stateless Streamable HTTP mode, mounted at `/mcp` in the
  FastAPI app. It exposes read-only tools, catalog/table resources and an `analyze-table` prompt.
- Use the official **A2A Python SDK** (`a2a-sdk` 1.x, protocol 1.0 JSON-RPC). Every agent gets its own card and
  endpoint at `/a2a/{agentId}`, and the platform card at `/.well-known/agent-card.json` advertises the router agent.
- Serve REST, MCP and A2A from **one process and one port**, all calling the same services.
- The sample client uses the matching official **client** SDKs.

## Consequences

- Positive: spec compliance and upgrades come from the SDKs, and the three protocols behave the same way. One
  container to deploy.
- Negative: two fast-moving SDKs to track (Dependabot groups the updates). MCP DNS-rebinding protection and A2A
  card URLs depend on host configuration (`DATAPLATFORM_MCP_ALLOWED_HOSTS`, `DATAPLATFORM_PUBLIC_BASE_URL`).

## Alternatives considered

- **Separate MCP and A2A services**: more to deploy, and logic would be duplicated or need an internal API.
- **FastMCP standalone**: equivalent MCP support, but an extra dependency next to the official SDK.
