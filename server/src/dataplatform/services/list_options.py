"""Collection query options shared by every paginated endpoint: paging, sorting, search, filters."""

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from dataplatform.domain.errors import InvalidRequestError
from dataplatform.domain.models import Page

FilterOp = Literal[
    "contains", "equals", "startsWith", "endsWith", "eq", "neq", "gt", "gte", "lt", "lte", "isEmpty", "isNotEmpty"
]
FILTER_OPS: frozenset[str] = frozenset(FilterOp.__args__)  # type: ignore[attr-defined]
TEXT_OPS: frozenset[str] = frozenset({"contains", "equals", "startsWith", "endsWith"})
_FILTER_PARAM = re.compile(r"^filter\[(?P<column>[A-Za-z_][A-Za-z0-9_]*)\](?:\[(?P<op>[A-Za-z]+)\])?$")
MAX_FILTER_VALUE_LENGTH = 200


@dataclass(frozen=True)
class ColumnFilter:
    """A single ``filter[column][op]=value`` condition."""

    column: str
    op: FilterOp | None
    value: str


@dataclass(frozen=True)
class ListOptions:
    """Validated paging, sorting, search and filter options."""

    page: int = 1
    page_size: int = 25
    sort: str | None = None
    order: Literal["asc", "desc"] = "asc"
    q: str | None = None
    filters: tuple[ColumnFilter, ...] = field(default_factory=tuple)

    @property
    def offset(self) -> int:
        """Zero-based row offset of the first item of the page."""
        return (self.page - 1) * self.page_size


def parse_filters(params: Iterable[tuple[str, str]]) -> tuple[ColumnFilter, ...]:
    """Extract ``filter[col]=v`` and ``filter[col][op]=v`` pairs from query parameters.

    Raises:
        InvalidRequestError: Unknown operator or value too long.
    """
    filters: list[ColumnFilter] = []
    for key, value in params:
        if not key.startswith("filter"):
            continue
        match = _FILTER_PARAM.match(key)
        if match is None:
            raise InvalidRequestError(f"Malformed filter parameter '{key}'. Use filter[column] or filter[column][op].")
        op = match.group("op")
        if op is not None and op not in FILTER_OPS:
            raise InvalidRequestError(f"Unknown filter operator '{op}'. Allowed: {', '.join(sorted(FILTER_OPS))}.")
        if len(value) > MAX_FILTER_VALUE_LENGTH:
            raise InvalidRequestError(f"Filter value for '{match.group('column')}' is too long.")
        filters.append(ColumnFilter(column=match.group("column"), op=op, value=value))  # type: ignore[arg-type]
    return tuple(filters)


def _matches(value: Any, op: str, expected: str) -> bool:
    if op == "isEmpty":
        return value is None or value == ""
    if op == "isNotEmpty":
        return not (value is None or value == "")
    if value is None:
        return False
    if op in TEXT_OPS or (isinstance(value, str) and op in ("eq", "neq")):
        text, needle = str(value).lower(), expected.lower()
        return {
            "contains": needle in text,
            "equals": text == needle,
            "eq": text == needle,
            "neq": text != needle,
            "startsWith": text.startswith(needle),
            "endsWith": text.endswith(needle),
        }[op]
    comparable: Any
    target: Any
    if isinstance(value, bool):
        comparable, target = value, expected.lower() in ("true", "1", "yes")
    elif isinstance(value, int | float):
        try:
            comparable, target = float(value), float(expected)
        except ValueError as exc:
            raise InvalidRequestError(f"'{expected}' is not a number.") from exc
    elif isinstance(value, datetime | date):
        comparable, target = value.isoformat(), expected
    else:
        comparable, target = str(value), expected
    return {
        "eq": comparable == target,
        "neq": comparable != target,
        "gt": comparable > target,
        "gte": comparable >= target,
        "lt": comparable < target,
        "lte": comparable <= target,
    }[op]


def paginate_in_memory[T](
    items: Sequence[T],
    options: ListOptions,
    *,
    fields: Mapping[str, Callable[[T], Any]],
    search_fields: Sequence[str],
) -> Page[T]:
    """Sort, filter, search and page an in-memory collection.

    Args:
        items: The full collection.
        options: Validated list options.
        fields: Allowlist of sortable/filterable field names and their accessors.
        search_fields: Fields searched by the global ``q`` parameter.

    Raises:
        InvalidRequestError: Unknown sort or filter field.
    """
    result = list(items)
    for flt in options.filters:
        getter = fields.get(flt.column)
        if getter is None:
            raise InvalidRequestError(f"Cannot filter on '{flt.column}'. Allowed: {', '.join(fields)}.")
        default_op = "contains" if all(isinstance(getter(i), str) for i in result[:1]) else "eq"
        op = flt.op or default_op
        result = [i for i in result if _matches(getter(i), op, flt.value)]
    if options.q:
        needle = options.q.lower()
        result = [i for i in result if any(needle in str(fields[f](i) or "").lower() for f in search_fields)]
    if options.sort:
        getter = fields.get(options.sort)
        if getter is None:
            raise InvalidRequestError(f"Cannot sort on '{options.sort}'. Allowed: {', '.join(fields)}.")
        present = [i for i in result if getter(i) is not None]
        missing = [i for i in result if getter(i) is None]
        present.sort(key=getter, reverse=options.order == "desc")
        result = present + missing
    window = result[options.offset : options.offset + options.page_size]
    return Page[T](items=window, total=len(result), page=options.page, page_size=options.page_size)
