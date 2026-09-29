# ADR-0002: Use deterministic rule-based agents instead of an LLM

- Status: Accepted
- Date: 2026-09-29

## Context

Data platforms now ship AI assistants (Databricks Genie, Snowflake Cortex Analyst). The mockup needs agents that
answer natural-language questions over the sample data, over REST, MCP and A2A. The mockup must also run
offline, cost nothing, need no secrets, and give reproducible answers so tests and demos are stable.

## Decision

- Implement four **rule-based agents**:
  - `data-analyst`: router and catalog explorer.
  - `sales-insights`, `supply-chain`, `quality-maintenance`: domain specialists.
- Each agent matches the question against keyword patterns for its skills and extracts parameters (top-N,
  months, catalog vocabulary). It builds SQL only from its own templates, those validated values and catalog
  metadata, never from raw user text. The SQL runs through the same sandboxed engine.
- Every reply carries a Markdown answer, the **SQL it ran**, the result columns and rows, and the skill id. The A2A
  artifact carries the same data as a JSON part.
- Agents can be enabled or disabled at run time from the settings.

## Consequences

- Positive: deterministic, testable and free. Answers are explainable because the SQL is shown. Client
  applications can exercise real MCP/A2A flows without an LLM.
- Negative: only phrasings the patterns know are understood. Unmatched questions get a helpful fallback
  listing the supported skills.
- Follow-up: an optional LLM-backed agent (for example Microsoft Foundry with a managed identity) behind the same
  `Agent` interface, selected by configuration.

## Alternatives considered

- **LLM agent with tool calling**: realistic, but needs keys or cloud access, is non-deterministic and costs money
  per call.
- **Canned answers**: deterministic, but the answers would not come from the data and would go stale.
