"""The DuckDB engine sandbox only runs single, read-only statements."""

import pytest

from dataplatform.container import Container
from dataplatform.domain.errors import QueryError, QueryTimeoutError
from dataplatform.infrastructure.catalog_metadata import all_tables
from dataplatform.infrastructure.sample_data import generate_sample_data


def should_load_every_table_when_engine_starts(container: Container) -> None:
    # Arrange
    tables = all_tables()

    # Act
    counts = {t.full_name: container.engine.row_count(t.full_name) for t in tables}

    # Assert
    assert len(counts) == 17
    assert all(count > 0 for count in counts.values())
    assert counts["retail.sales.orders"] == 15_000


def should_generate_identical_data_when_seed_is_identical() -> None:
    # Arrange / Act
    first = generate_sample_data(7).tables["retail.sales.orders"][:50]
    second = generate_sample_data(7).tables["retail.sales.orders"][:50]

    # Assert
    assert first == second


def should_return_rows_and_types_when_select_is_valid(container: Container) -> None:
    # Act
    result = container.engine.execute(
        "SELECT store_id, opened_date FROM retail.sales.stores WHERE region = ? ORDER BY store_id",
        ["North"],
        max_rows=100,
        timeout_seconds=5,
    )

    # Assert
    assert result.columns == [("store_id", "VARCHAR"), ("opened_date", "DATE")]
    assert result.rows
    assert isinstance(result.rows[0]["opened_date"], str)
    assert not result.truncated


def should_flag_truncation_when_more_rows_than_max(container: Container) -> None:
    # Act
    result = container.engine.execute("SELECT * FROM retail.sales.orders", max_rows=10, timeout_seconds=5)

    # Assert
    assert len(result.rows) == 10
    assert result.truncated


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE retail.sales.orders",
        "DELETE FROM retail.sales.orders",
        "INSERT INTO retail.sales.stores VALUES ('x')",
        "UPDATE retail.sales.orders SET status = 'x'",
        "CREATE TABLE retail.sales.hack AS SELECT 1",
        "ATTACH ':memory:' AS other",
        "COPY retail.sales.orders TO '/tmp/out.csv'",
        "SET threads = 1",
        "PRAGMA threads = 1",
        "INSTALL httpfs",
        "SELECT 1; DROP TABLE retail.sales.orders",
    ],
)
def should_reject_statement_when_not_single_select(container: Container, sql: str) -> None:
    # Act / Assert
    with pytest.raises(QueryError):
        container.engine.execute(sql, max_rows=10, timeout_seconds=5)
    assert container.engine.row_count("retail.sales.orders") == 15_000


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM read_text('/etc/hostname')",
        "SELECT * FROM glob('/*')",
    ],
)
def should_block_file_access_when_external_access_disabled(container: Container, sql: str) -> None:
    # Act / Assert
    with pytest.raises(QueryError):
        container.engine.execute(sql, max_rows=10, timeout_seconds=5)


def should_hide_internal_details_when_sql_is_invalid(container: Container) -> None:
    # Act
    with pytest.raises(QueryError) as caught:
        container.engine.execute("SELECT * FROM retail.sales.missing", max_rows=10, timeout_seconds=5)

    # Assert
    assert "missing" in caught.value.detail
    assert "Traceback" not in caught.value.detail


def should_interrupt_query_when_timeout_exceeded(container: Container) -> None:
    # Arrange
    slow = "SELECT count(*) FROM range(1000000000) a, range(1000) b WHERE a.range * b.range % 7 = 3"

    # Act / Assert
    with pytest.raises(QueryTimeoutError):
        container.engine.execute(slow, max_rows=10, timeout_seconds=0.2)
