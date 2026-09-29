# Contributing

Thanks for helping improve the data platform mockup. This project follows the
[ai-coding-standards](https://github.com/frkim/ai-coding-standards); [AGENTS.md](AGENTS.md) summarises them for
this repository.

## Workflow

1. Open or pick an issue that describes the change.
2. Branch off `main` as `feature/<issue>-<slug>`, `fix/<issue>-<slug>` or `chore/<slug>`.
3. Make a small, focused change. Add or update tests with it; a bug fix starts with a failing regression test.
4. Run the quality gates for every part you touched (below), and exercise the feature by hand.
5. Update the relevant README or ADR in the same pull request.
6. Open a pull request with a [Conventional Commit](https://www.conventionalcommits.org) title such as
   `feat(server): add sensor summary tool`. Describe what changed, why and how you verified it, and link
   `Closes #<issue>`.

Pull requests are squash-merged after one code-owner approval and green CI (lint, type-check, test, build,
CodeQL).

## Quality gates

```bash
# server/ and sample-client/
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests && uv run pytest

# web/
npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
```

## Conventions

- **Python**: type hints everywhere (`mypy --strict`), Google-style docstrings on public APIs, ruff for lint and
  format. Tests are named `should_<behaviour>`.
- **TypeScript**: `strict` mode, ESLint + Prettier, Vitest for unit tests.
- **Layers** (server): `api`/`protocols` → `services` → `agents`/`domain` → `infrastructure`. Dependencies
  point inwards.
- **Sample data** must stay deterministic for a given seed, and consistent across tables.
- **Architecture decisions** are recorded in [`docs/adr/`](docs/adr/). Add a new ADR rather than editing an
  accepted one.
- Throwaway scripts go in `tmp/scripts/` (git-ignored).

## Reporting security issues

Do not open a public issue; see [SECURITY.md](SECURITY.md).
