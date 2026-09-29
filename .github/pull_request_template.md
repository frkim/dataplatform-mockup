## What changed

<!-- A short summary of the change. -->

## Why

<!-- The problem it solves. Link the issue: Closes #123 -->

## How it was verified

- [ ] `server/`: `uv run ruff check . && uv run ruff format --check . && uv run mypy src tests && uv run pytest`
- [ ] `sample-client/`: same commands
- [ ] `web/`: `npm run lint && npm run format:check && npm run typecheck && npm test && npm run build`
- [ ] Exercised the feature manually (describe what you observed)

## Risk and follow-up

<!-- Breaking changes, migrations, docs or ADRs updated. -->
