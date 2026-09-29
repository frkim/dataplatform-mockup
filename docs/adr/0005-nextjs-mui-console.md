# ADR-0005: Next.js + Material UI console behind same-origin rewrites

- Status: Accepted
- Date: 2026-09-29

## Context

The issue asks for a front-end to browse data and configure settings. The UI standards require Material UI with
one theme, a persisted dark/light toggle, and data tables with header sorting/filtering, pagination and a global
search.

## Decision

- **Next.js (App Router, TypeScript strict)** with **Material UI** CSS-variable theming and **MUI DataGrid** in
  server-side mode: sorting, filtering, paging and search are pushed to the REST API. **D3.js** draws the
  revenue chart.
- The browser only calls its own origin. Next.js rewrites `/api/v1/*` and `/health/*` to `PLATFORM_API_URL`.
  This avoids CORS in production and allows a strict Content-Security-Policy with `connect-src 'self'`.
- Standalone output in a non-root Node 24 container.

## Consequences

- Positive: one origin for the browser, a strict CSP, and the same code for local dev and containers.
- Negative: `PLATFORM_API_URL` is baked in at build time for the standalone image (a build argument in Compose).

## Alternatives considered

- **Vue.js + Vuetify**: also allowed by the standards; Next.js was chosen for MUI DataGrid's server-side mode.
- **Direct browser → API calls with CORS**: works in development, but needs CORS and a looser CSP in every
  environment.
