# Data Platform Mockup Web Console

Next.js web console for the mock data platform. It provides a professional browser UI for synthetic manufacturing and retail data, SQL exploration, AI agents, query history, and platform settings. The app uses the Next.js App Router, TypeScript, Material UI CSS-variable theming, MUI DataGrid, D3, and Vitest.

## Pages

- **Dashboard** (`/`) — platform stat cards, REST/MCP/A2A/OpenAPI endpoints, a D3 monthly revenue chart, and an AI agent summary.
- **Data Explorer** (`/explorer`) — catalog/schema/table tree, deep links with `?table=catalog.schema.table`, server-side row DataGrid, and schema grid.
- **SQL Worksheet** (`/sql`) — read-only SQL editor, sample queries, query execution, result metadata, and result grid.
- **AI Agents** (`/agents`) — agent cards, example prompts, chat invocation, generated SQL, and compact result grid.
- **Query History** (`/history`) — server-side searchable/sortable/filterable query history grid.
- **Settings** (`/settings`) — platform settings form plus MCP and A2A connection snippets.

## Backend configuration

Set `PLATFORM_API_URL` to the backend origin when running or building the app:

```bash
PLATFORM_API_URL=http://localhost:8000
```

`next.config.ts` rewrites same-origin browser requests to the backend:

- `/api/v1/:path*` → `${PLATFORM_API_URL}/api/v1/:path*`
- `/health/:path*` → `${PLATFORM_API_URL}/health/:path*`

See `.env.example` for the local default.

## Scripts

```bash
npm run dev           # Start Next.js dev server
npm run build         # Production build
npm run start         # Start the production server
npm run lint          # ESLint
npm run typecheck     # next typegen (route types) + tsc --noEmit
npm test              # Vitest test suite
npm run format:check  # Prettier check
```

## Project structure

```text
web/
├── next.config.ts          # rewrites, standalone output, security headers
├── package.json            # scripts and dependencies
├── src/
│   ├── app/                # App Router pages and root providers
│   │   ├── agents/
│   │   ├── explorer/
│   │   ├── history/
│   │   ├── settings/
│   │   └── sql/
│   ├── components/         # shell, shared UI states, chart, markdown renderer
│   ├── lib/                # API client, API types, DataGrid query helpers, formatting
│   ├── test/               # Vitest setup
│   └── theme/              # single Material UI theme
├── public/                 # static assets
└── vitest.config.ts        # test runner configuration
```
