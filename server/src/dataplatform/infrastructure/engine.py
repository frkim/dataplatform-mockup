"""DuckDB-backed query engine emulating a three-level ``catalog.schema.table`` warehouse.

Each catalog is an attached in-memory DuckDB database. Once the sample data is loaded the
engine is sandboxed: external file/network access is disabled and the configuration is
locked, so user SQL cannot read the host file system or re-enable access.
"""

import csv
import logging
import shutil
import tempfile
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import duckdb

from dataplatform.domain.errors import QueryError, QueryTimeoutError
from dataplatform.infrastructure.catalog_metadata import CATALOGS, TableDef, all_tables
from dataplatform.infrastructure.sample_data import SampleData

logger = logging.getLogger(__name__)

_READ_ONLY_STATEMENTS = frozenset({duckdb.StatementType.SELECT})


@dataclass(frozen=True)
class RawResult:
    """Rows returned by the engine, already converted to JSON-friendly values."""

    columns: list[tuple[str, str]]
    rows: list[dict[str, Any]]
    truncated: bool


def to_json_value(value: Any) -> Any:
    """Convert a DuckDB value to a JSON-serialisable Python value."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list | tuple):
        return [to_json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_json_value(v) for k, v in value.items()}
    return str(value)


def _csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else value


class Engine:
    """Thread-safe, read-only SQL engine over the mock catalog."""

    def __init__(self, sample_data: SampleData, *, memory_limit: str = "1GB", threads: int = 4) -> None:
        self._connection = duckdb.connect(":memory:")
        self._row_counts: dict[str, int] = {}
        self._load(sample_data)
        self._sandbox(memory_limit, threads)

    def _load(self, sample_data: SampleData) -> None:
        con = self._connection
        staging = Path(tempfile.mkdtemp(prefix="dataplatform-"))
        try:
            for catalog in CATALOGS:
                con.execute(f"ATTACH ':memory:' AS \"{catalog.name}\"")
                for schema in catalog.schemas:
                    con.execute(f'CREATE SCHEMA "{catalog.name}"."{schema.name}"')
            for table in all_tables():
                self._create_and_load(table, sample_data.tables[table.full_name], staging)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        con.execute("USE memory")

    def _create_and_load(self, table: TableDef, rows: Sequence[Sequence[Any]], staging: Path) -> None:
        con = self._connection
        column_ddl = ", ".join(
            f'"{c.name}" {c.type}{"" if c.nullable else " NOT NULL"}{" PRIMARY KEY" if c.primary_key else ""}'
            for c in table.columns
        )
        con.execute(f"CREATE TABLE {table.quoted_name} ({column_ddl})")
        con.execute(f"COMMENT ON TABLE {table.quoted_name} IS $${table.description}$$")
        for column in table.columns:
            con.execute(f'COMMENT ON COLUMN {table.quoted_name}."{column.name}" IS $${column.description}$$')
        path = staging / f"{table.full_name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows([_csv_value(v) for v in row] for row in rows)
        types = ", ".join(f"'{c.name}': '{c.type}'" for c in table.columns)
        con.execute(
            f"INSERT INTO {table.quoted_name} SELECT * FROM read_csv(?, header = false, columns = {{{types}}})",  # noqa: S608
            [str(path)],
        )
        self._row_counts[table.full_name] = len(rows)

    def _sandbox(self, memory_limit: str, threads: int) -> None:
        con = self._connection
        con.execute(f"SET memory_limit = '{memory_limit}'")
        con.execute(f"SET threads = {int(threads)}")
        con.execute("SET enable_external_access = false")
        con.execute("SET autoinstall_known_extensions = false")
        con.execute("SET autoload_known_extensions = false")
        con.execute("SET lock_configuration = true")

    @property
    def version(self) -> str:
        """DuckDB library version."""
        return str(duckdb.__version__)

    def row_count(self, full_name: str) -> int:
        """Return the number of rows in a table (tables are immutable after load)."""
        return self._row_counts[full_name]

    def execute(
        self,
        sql: str,
        parameters: Sequence[Any] | None = None,
        *,
        max_rows: int,
        timeout_seconds: float,
    ) -> RawResult:
        """Execute a single read-only statement.

        Args:
            sql: One ``SELECT`` (or ``WITH ... SELECT``) statement.
            parameters: Positional ``?`` parameters.
            max_rows: Maximum rows to return; ``truncated`` is set when more exist.
            timeout_seconds: The statement is interrupted after this delay.

        Raises:
            QueryError: The statement is not a single read-only statement or fails.
            QueryTimeoutError: The statement exceeded ``timeout_seconds``.

        """
        cursor = self._connection.cursor()
        try:
            self._ensure_read_only(cursor, sql)
            timed_out = threading.Event()

            def _interrupt() -> None:
                timed_out.set()
                cursor.interrupt()

            timer = threading.Timer(timeout_seconds, _interrupt)
            timer.start()
            try:
                cursor.execute(sql, list(parameters) if parameters else None)
                description = cursor.description or []
                fetched = cursor.fetchmany(max_rows + 1)
            except duckdb.InterruptException as exc:
                raise QueryTimeoutError(f"Query exceeded the {timeout_seconds:g} s timeout.") from exc
            except duckdb.Error as exc:
                if timed_out.is_set():
                    raise QueryTimeoutError(f"Query exceeded the {timeout_seconds:g} s timeout.") from exc
                raise QueryError(_clean_error(exc)) from exc
            finally:
                timer.cancel()
        finally:
            cursor.close()
        columns = [(str(d[0]), str(d[1])) for d in description]
        names = [c[0] for c in columns]
        rows = [{n: to_json_value(v) for n, v in zip(names, row, strict=True)} for row in fetched[:max_rows]]
        return RawResult(columns=columns, rows=rows, truncated=len(fetched) > max_rows)

    @staticmethod
    def _ensure_read_only(cursor: duckdb.DuckDBPyConnection, sql: str) -> None:
        try:
            statements = cursor.extract_statements(sql)
        except duckdb.Error as exc:
            raise QueryError(_clean_error(exc)) from exc
        if len(statements) != 1:
            raise QueryError("Exactly one SQL statement is allowed per request.")
        if statements[0].type not in _READ_ONLY_STATEMENTS:
            raise QueryError("Only read-only SELECT statements are allowed on this platform.")


def _clean_error(exc: Exception) -> str:
    """Return the first line of a DuckDB error, without internal stack details."""
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    return message[:500]
