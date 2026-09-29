# Security policy

## Supported versions

Only the latest commit on `main` is supported.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through
[GitHub private vulnerability reporting](https://github.com/frkim/dataplatform-mockup/security/advisories/new).
Include the affected component (`server`, `web` or `sample-client`), reproduction steps and the impact you
observed. You will get an acknowledgement within five working days.

## Security model

This is a **local mock** with synthetic data and **no authentication** (see
[ADR-0004](docs/adr/0004-no-auth-local-mock.md)). Keep it on `localhost`, or put it behind an identity-aware
proxy (for example Azure Container Apps authentication with Microsoft Entra ID) before exposing it.

Built-in safeguards:

- User SQL is limited to a single read-only `SELECT`. DuckDB external access, extension auto-loading and
  configuration changes are disabled. Queries have a timeout, a row cap and memory/thread limits.
- Every input is validated, and errors are RFC 9457 problem details that do not leak stack traces.
- CORS uses an explicit origin allow-list (wildcards are rejected). MCP has DNS-rebinding protection. Security
  headers (CSP, `X-Content-Type-Options`, `Referrer-Policy`, …) are set on the API and the web console.
- Containers run as non-root users; Compose binds ports to `127.0.0.1` and runs the server read-only.
- Dependabot, CodeQL and secret scanning run on the repository.
