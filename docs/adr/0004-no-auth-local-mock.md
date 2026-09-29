# ADR-0004: No authentication for the local mock

- Status: Accepted
- Date: 2026-09-29

## Context

The platform serves only synthetic data, and its SQL surface is read-only. It is meant for local prototyping,
where MCP hosts, A2A clients and the console should connect without setting up credentials. The security
standards still require protection wherever the service is reachable by others.

## Decision

- The mockup has **no authentication or authorisation** of its own. Settings changes are allowed to any caller.
- Defence in depth stays on:
  - The server binds to `127.0.0.1` by default.
  - Compose publishes ports on `127.0.0.1` only.
  - CORS uses an explicit allow-list, and MCP has DNS-rebinding protection.
  - The SQL sandbox, input validation and security headers stay enabled.
- Any shared deployment **must** sit behind an identity-aware front door, for example Azure Container Apps
  built-in authentication with Microsoft Entra ID. A2A cards would then declare the matching security scheme.

## Consequences

- Positive: frictionless local use, and simple client samples.
- Negative: not safe to expose publicly as is. This is documented in the README and SECURITY.md.
- Follow-up: Entra ID (OAuth 2.0 bearer) support in the MCP and A2A surfaces when an Azure deployment is added.

## Alternatives considered

- **API keys**: they add secret handling to every client sample, and still need rotation and storage.
- **Entra ID now**: requires a tenant and app registrations just to try the mockup.
