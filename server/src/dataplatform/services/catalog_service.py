"""Catalog browsing: catalogs, schemas, tables, and paged table rows."""

from typing import Any

from dataplatform.domain.errors import InvalidRequestError, NotFoundError, QueryError
from dataplatform.domain.models import Catalog, Column, Page, PlatformStats, Schema, TableDetail, TableSummary
from dataplatform.infrastructure.catalog_metadata import CATALOGS, CatalogDef, ColumnDef, SchemaDef, TableDef
from dataplatform.infrastructure.engine import Engine
from dataplatform.services.list_options import TEXT_OPS, ColumnFilter, ListOptions, paginate_in_memory
from dataplatform.services.settings_service import SettingsService

_SQL_COMPARATORS = {"eq": "=", "neq": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


class CatalogService:
    """Read-only access to the catalog metadata and table contents."""

    def __init__(self, engine: Engine, settings: SettingsService, *, timeout_seconds: float) -> None:
        self._engine = engine
        self._settings = settings
        self._timeout = timeout_seconds

    # Metadata -----------------------------------------------------------------------------

    def _catalog(self, name: str) -> CatalogDef:
        catalog = next((c for c in CATALOGS if c.name == name), None)
        if catalog is None:
            raise NotFoundError(f"Catalog '{name}' does not exist.")
        return catalog

    def _schema(self, catalog: str, name: str) -> SchemaDef:
        schema = next((s for s in self._catalog(catalog).schemas if s.name == name), None)
        if schema is None:
            raise NotFoundError(f"Schema '{catalog}.{name}' does not exist.")
        return schema

    def table_def(self, catalog: str, schema: str, name: str) -> TableDef:
        """Return a table definition.

        Raises:
            NotFoundError: The table does not exist.
        """
        table = next((t for t in self._schema(catalog, schema).tables if t.name == name), None)
        if table is None:
            raise NotFoundError(f"Table '{catalog}.{schema}.{name}' does not exist.")
        return table

    def resolve(self, full_name: str) -> TableDef:
        """Resolve a ``catalog.schema.table`` name.

        Raises:
            InvalidRequestError: The name is not a three-part name.
            NotFoundError: The table does not exist.
        """
        parts = full_name.strip().split(".")
        if len(parts) != 3 or not all(parts):
            raise InvalidRequestError(f"'{full_name}' is not a three-part name (catalog.schema.table).")
        return self.table_def(*parts)

    def list_catalogs(self, options: ListOptions) -> Page[Catalog]:
        """List catalogs."""
        items = [Catalog(name=c.name, description=c.description, schema_count=len(c.schemas)) for c in CATALOGS]
        return paginate_in_memory(
            items,
            options,
            fields={"name": lambda c: c.name, "description": lambda c: c.description, "schemaCount": lambda c: c.schema_count},
            search_fields=("name", "description"),
        )

    def list_schemas(self, catalog: str, options: ListOptions) -> Page[Schema]:
        """List the schemas of a catalog."""
        items = [
            Schema(catalog=s.catalog, name=s.name, description=s.description, table_count=len(s.tables))
            for s in self._catalog(catalog).schemas
        ]
        return paginate_in_memory(
            items,
            options,
            fields={"name": lambda s: s.name, "description": lambda s: s.description, "tableCount": lambda s: s.table_count},
            search_fields=("name", "description"),
        )

    def _summary(self, table: TableDef) -> TableSummary:
        return TableSummary(
            catalog=table.catalog,
            schema=table.schema,
            name=table.name,
            full_name=table.full_name,
            description=table.description,
            row_count=self._engine.row_count(table.full_name),
            column_count=len(table.columns),
        )

    def list_tables(self, catalog: str, schema: str, options: ListOptions) -> Page[TableSummary]:
        """List the tables of a schema."""
        items = [self._summary(t) for t in self._schema(catalog, schema).tables]
        return paginate_in_memory(
            items,
            options,
            fields={
                "name": lambda t: t.name,
                "description": lambda t: t.description,
                "rowCount": lambda t: t.row_count,
                "columnCount": lambda t: t.column_count,
            },
            search_fields=("name", "description"),
        )

    def all_table_summaries(self) -> list[TableSummary]:
        """Return every table of every catalog."""
        return [self._summary(t) for c in CATALOGS for s in c.schemas for t in s.tables]

    def get_table(self, catalog: str, schema: str, name: str) -> TableDetail:
        """Return a table with its columns."""
        table = self.table_def(catalog, schema, name)
        return TableDetail(
            **self._summary(table).model_dump(),
            columns=[
                Column(name=c.name, type=c.type, description=c.description, nullable=c.nullable, primary_key=c.primary_key)
                for c in table.columns
            ],
        )

    def stats(self) -> PlatformStats:
        """Aggregate counts over the catalog."""
        tables = self.all_table_summaries()
        return PlatformStats(
            catalogs=len(CATALOGS),
            schemas=sum(len(c.schemas) for c in CATALOGS),
            tables=len(tables),
            total_rows=sum(t.row_count for t in tables),
        )

    # Rows ---------------------------------------------------------------------------------

    def query_rows(self, catalog: str, schema: str, name: str, options: ListOptions) -> Page[dict[str, Any]]:
        """Return a page of table rows with server-side sorting, filtering and global search.

        Raises:
            NotFoundError: The table does not exist.
            InvalidRequestError: Unknown sort/filter column or invalid filter value.
        """
        table = self.table_def(catalog, schema, name)
        where, params = build_where(table, options)
        order_by = build_order_by(table, options)
        engine_rows = options.page_size
        self._settings.simulate_latency()
        try:
            count = self._engine.execute(
                f"SELECT count(*) AS total FROM {table.quoted_name}{where}",
                params,
                max_rows=1,
                timeout_seconds=self._timeout,
            )
            page = self._engine.execute(
                f"SELECT * FROM {table.quoted_name}{where}{order_by} LIMIT ? OFFSET ?",
                [*params, options.page_size, options.offset],
                max_rows=engine_rows,
                timeout_seconds=self._timeout,
            )
        except QueryError as exc:
            if "Conversion Error" in exc.detail or "Could not convert" in exc.detail:
                raise InvalidRequestError(f"Invalid filter value: {exc.detail}") from exc
            raise
        return Page[dict[str, Any]](
            items=page.rows, total=int(count.rows[0]["total"]), page=options.page, page_size=options.page_size
        )


def _column(table: TableDef, name: str, purpose: str) -> ColumnDef:
    column = table.column(name)
    if column is None:
        allowed = ", ".join(c.name for c in table.columns)
        raise InvalidRequestError(f"Cannot {purpose} on unknown column '{name}'. Allowed: {allowed}.")
    return column


def _condition(column: ColumnDef, flt: ColumnFilter) -> tuple[str, list[Any]]:
    ident = f'"{column.name}"'
    as_text = f"lower(CAST({ident} AS VARCHAR))"
    op = flt.op or ("contains" if column.is_text else "eq")
    if op == "isEmpty":
        return f"({ident} IS NULL OR CAST({ident} AS VARCHAR) = '')", []
    if op == "isNotEmpty":
        return f"({ident} IS NOT NULL AND CAST({ident} AS VARCHAR) <> '')", []
    if op in TEXT_OPS:
        value = flt.value.lower()
        return {
            "contains": (f"contains({as_text}, ?)", [value]),
            "equals": (f"{as_text} = ?", [value]),
            "startsWith": (f"starts_with({as_text}, ?)", [value]),
            "endsWith": (f"suffix({as_text}, ?)", [value]),
        }[op]
    if column.is_text:
        return f"{as_text} {_SQL_COMPARATORS[op]} ?", [flt.value.lower()]
    # Identifier and type come from the allowlisted metadata, never from the client.
    return f"{ident} {_SQL_COMPARATORS[op]} CAST(? AS {column.type})", [flt.value]


def build_where(table: TableDef, options: ListOptions) -> tuple[str, list[Any]]:
    """Build a parameterised ``WHERE`` clause from filters and the global search term."""
    clauses: list[str] = []
    params: list[Any] = []
    for flt in options.filters:
        sql, values = _condition(_column(table, flt.column, "filter"), flt)
        clauses.append(sql)
        params.extend(values)
    if options.q:
        text_columns = [c for c in table.columns if c.is_text]
        if text_columns:
            clauses.append("(" + " OR ".join(f'contains(lower("{c.name}"), ?)' for c in text_columns) + ")")
            params.extend([options.q.lower()] * len(text_columns))
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


def build_order_by(table: TableDef, options: ListOptions) -> str:
    """Build a deterministic ``ORDER BY`` clause (requested column, then the primary key)."""
    keys: list[str] = []
    if options.sort:
        column = _column(table, options.sort, "sort")
        keys.append(f'"{column.name}" {"DESC" if options.order == "desc" else "ASC"} NULLS LAST')
    keys.extend(f'"{c.name}" ASC' for c in table.columns if c.primary_key or not any(k.primary_key for k in table.columns))
    return " ORDER BY " + ", ".join(dict.fromkeys(keys)) if keys else ""

