# ADR-0001: Use an in-memory DuckDB engine with generated sample data

- Status: Accepted
- Date: 2026-09-29

## Context

The mockup has to behave like a warehouse or lakehouse (Snowflake, Databricks): three-part names
(`catalog.schema.table`), ANSI SQL with analytic functions, and fast aggregations over tens of thousands of rows.
It must also start with one command, need no cloud account, and give every developer and test the same data.

## Decision

- Run **DuckDB in-memory**, one database per catalog (`manufacturing`, `retail`), attached to one connection, so
  SQL uses real three-part names.
- **Generate** the sample data at start-up from a fixed seed (`DATAPLATFORM_DATA_SEED`). The data is realistic
  and referentially consistent (orders → stores/products/customers, sensor drift → degraded machines).
  Load it through typed CSV bulk inserts.
- **Sandbox** the engine. Only a single `SELECT` statement per request, external access and extension
  auto-loading disabled, configuration locked, memory/thread limits, a per-query timeout and a row cap.

## Consequences

- Positive: zero infrastructure, sub-second start-up, identical data in tests, CI and demos, and a real SQL
  dialect for agents and users.
- Negative: data and settings are lost on restart, and one process holds everything in memory (about 100k rows,
  far below the 1 GB default limit).
- Follow-up: optional Parquet export/import if persistent or larger datasets are needed.

## Alternatives considered

- **SQLite**: no three-part names, weaker analytic SQL.
- **PostgreSQL in a container**: heavier set-up, and needs seeding migrations and credentials.
- **Static CSV/Parquet files in the repository**: large diffs, and hard to keep consistent when the schema changes.
