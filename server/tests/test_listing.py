"""Listing: filters, search, sorting and pagination (in memory and in SQL)."""

import pytest

from dataplatform.container import Container
from dataplatform.domain.errors import InvalidRequestError, NotFoundError
from dataplatform.services.catalog_service import build_where
from dataplatform.services.list_options import ColumnFilter, ListOptions, paginate_in_memory, parse_filters

ITEMS = [{"name": "alpha", "size": 3}, {"name": "beta", "size": 10}, {"name": "gamma", "size": 7}]
FIELDS = {"name": lambda i: i["name"], "size": lambda i: i["size"]}


def should_parse_filters_when_column_and_operator_are_given() -> None:
    # Act
    filters = parse_filters([("page", "2"), ("filter[region]", "North"), ("filter[total][gte]", "100")])

    # Assert
    assert filters == (ColumnFilter("region", None, "North"), ColumnFilter("total", "gte", "100"))


@pytest.mark.parametrize(
    "param",
    [("filter[region][drop]", "x"), ("filter[1bad]", "x"), ("filter[a;b]", "x"), ("filter[name]", "x" * 201)],
)
def should_reject_filter_when_malformed(param: tuple[str, str]) -> None:
    # Act / Assert
    with pytest.raises(InvalidRequestError):
        parse_filters([param])


def should_sort_filter_and_page_when_listing_in_memory() -> None:
    # Arrange
    options = ListOptions(page=1, page_size=1, sort="size", order="desc", filters=(ColumnFilter("size", "gt", "5"),))

    # Act
    page = paginate_in_memory(ITEMS, options, fields=FIELDS, search_fields=["name"])

    # Assert
    assert page.total == 2
    assert page.items == [{"name": "beta", "size": 10}]


def should_search_case_insensitively_when_q_is_given() -> None:
    # Act
    page = paginate_in_memory(ITEMS, ListOptions(q="GAM"), fields=FIELDS, search_fields=["name"])

    # Assert
    assert [i["name"] for i in page.items] == ["gamma"]


@pytest.mark.parametrize(
    "options", [ListOptions(sort="secret"), ListOptions(filters=(ColumnFilter("secret", None, "x"),))]
)
def should_reject_listing_when_field_not_allowlisted(options: ListOptions) -> None:
    # Act / Assert
    with pytest.raises(InvalidRequestError):
        paginate_in_memory(ITEMS, options, fields=FIELDS, search_fields=["name"])


def should_bind_values_as_parameters_when_building_where(container: Container) -> None:
    # Arrange
    table = container.catalog.table_def("retail", "sales", "stores")
    options = ListOptions(q="x' OR 1=1 --", filters=(ColumnFilter("region", "equals", "North'; DROP TABLE x"),))

    # Act
    where, params = build_where(table, options)

    # Assert
    assert "DROP" not in where
    assert "north'; drop table x" in params  # equals is case-insensitive


def should_page_rows_when_browsing_table(container: Container) -> None:
    # Arrange
    options = ListOptions(
        page=2,
        page_size=5,
        sort="total_amount",
        order="desc",
        filters=(ColumnFilter("channel", None, "online"), ColumnFilter("total_amount", "gte", "100")),
    )

    # Act
    page = container.catalog.query_rows("retail", "sales", "orders", options)

    # Assert
    assert page.page == 2
    assert len(page.items) == 5
    assert page.total > 5
    amounts = [row["total_amount"] for row in page.items]
    assert amounts == sorted(amounts, reverse=True)
    assert all(row["channel"] == "online" and row["total_amount"] >= 100 for row in page.items)


def should_search_text_columns_when_q_is_given(container: Container) -> None:
    # Act
    page = container.catalog.query_rows("manufacturing", "production", "plants", ListOptions(q="lyon"))

    # Assert
    assert [row["plant_id"] for row in page.items] == ["PL-LYO"]


@pytest.mark.parametrize(
    ("op", "value", "expected_min"),
    [("isEmpty", "", 0), ("isNotEmpty", "", 1), ("startsWith", "PL-", 1), ("endsWith", "LYO", 1), ("neq", "x", 1)],
)
def should_apply_operator_when_filtering_rows(container: Container, op: str, value: str, expected_min: int) -> None:
    # Arrange
    options = ListOptions(filters=(ColumnFilter("plant_id", op, value),))  # type: ignore[arg-type]

    # Act
    page = container.catalog.query_rows("manufacturing", "production", "plants", options)

    # Assert
    assert page.total >= expected_min


def should_reject_filter_when_value_has_wrong_type(container: Container) -> None:
    # Arrange
    options = ListOptions(filters=(ColumnFilter("total_amount", "gt", "lots"),))

    # Act / Assert
    with pytest.raises(InvalidRequestError):
        container.catalog.query_rows("retail", "sales", "orders", options)


@pytest.mark.parametrize("options", [ListOptions(sort="nope"), ListOptions(filters=(ColumnFilter("nope", None, "1"),))])
def should_reject_rows_query_when_column_unknown(container: Container, options: ListOptions) -> None:
    # Act / Assert
    with pytest.raises(InvalidRequestError):
        container.catalog.query_rows("retail", "sales", "orders", options)


def should_raise_not_found_when_table_unknown(container: Container) -> None:
    # Act / Assert
    with pytest.raises(NotFoundError):
        container.catalog.resolve("retail.sales.nope")


def should_reject_name_when_not_three_parts(container: Container) -> None:
    # Act / Assert
    with pytest.raises(InvalidRequestError):
        container.catalog.resolve("orders")
