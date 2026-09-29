import type { GridFilterModel, GridPaginationModel, GridSortModel } from "@mui/x-data-grid";

export type GridQueryInput = {
  paginationModel?: GridPaginationModel;
  sortModel?: GridSortModel;
  filterModel?: GridFilterModel;
  quickFilterValues?: unknown[];
  /** DataGrid column types by field, used to serialise date filter values. */
  columnTypes?: Record<string, string | undefined>;
};

const operatorMap: Record<string, string> = {
  contains: "contains",
  equals: "equals",
  startsWith: "startsWith",
  endsWith: "endsWith",
  isEmpty: "isEmpty",
  isNotEmpty: "isNotEmpty",
  "=": "eq",
  "!=": "neq",
  ">": "gt",
  ">=": "gte",
  "<": "lt",
  "<=": "lte",
  is: "eq",
  not: "neq",
  after: "gt",
  onOrAfter: "gte",
  before: "lt",
  onOrBefore: "lte",
};

/** Return whether the backend supports a DataGrid filter operator. */
export function isSupportedGridOperator(operator: string): boolean {
  return Object.hasOwn(operatorMap, operator);
}

const pad = (value: number) => String(value).padStart(2, "0");

/**
 * Serialise a filter value for the API. The DataGrid date input yields UTC midnight (`new Date("YYYY-MM-DD")`)
 * and the date-time input yields local time, so dates become `YYYY-MM-DD` and date-times local
 * `YYYY-MM-DD HH:mm:ss`, which is what the naive DuckDB `DATE`/`TIMESTAMP` casts expect.
 */
export function serializeFilterValue(value: unknown, columnType?: string): string {
  if (!(value instanceof Date)) return String(value);
  if (columnType === "dateTime") {
    return (
      `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())} ` +
      `${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`
    );
  }
  return value.toISOString().slice(0, 10);
}

const hasFilterValue = (operator: string, value: unknown) => {
  if (operator === "isEmpty" || operator === "isNotEmpty") return true;
  if (value === undefined || value === null) return false;
  if (typeof value === "string" && value.trim() === "") return false;
  if (Array.isArray(value) && value.length === 0) return false;
  return true;
};

/** Convert MUI DataGrid server models into backend collection query parameters. */
export function buildGridQuery({
  paginationModel,
  sortModel,
  filterModel,
  quickFilterValues,
  columnTypes,
}: GridQueryInput): URLSearchParams {
  const params = new URLSearchParams();
  if (paginationModel) {
    params.set("page", String(paginationModel.page + 1));
    params.set("pageSize", String(paginationModel.pageSize));
  }

  const sort = sortModel?.find((item) => item.sort);
  if (sort) {
    params.set("sort", sort.field);
    params.set("order", sort.sort ?? "asc");
  }

  const quickValues = quickFilterValues ?? filterModel?.quickFilterValues;
  const q = quickValues
    ?.map(String)
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
  if (q) params.set("q", q);

  for (const item of filterModel?.items ?? []) {
    if (!item.field || !isSupportedGridOperator(item.operator)) continue;
    const operator = operatorMap[item.operator];
    if (!hasFilterValue(item.operator, item.value)) continue;
    if (item.value instanceof Date && Number.isNaN(item.value.getTime())) continue;
    const value =
      item.operator === "isEmpty" || item.operator === "isNotEmpty"
        ? "true"
        : serializeFilterValue(item.value, columnTypes?.[item.field]);
    params.set(`filter[${item.field}][${operator}]`, value);
  }

  return params;
}

/** Return the backend operator name for a DataGrid operator. */
export function mapGridOperator(operator: string): string {
  return operatorMap[operator] ?? operator;
}
