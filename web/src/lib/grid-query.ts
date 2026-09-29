import type { GridFilterModel, GridPaginationModel, GridSortModel } from "@mui/x-data-grid";

export type GridQueryInput = {
  paginationModel?: GridPaginationModel;
  sortModel?: GridSortModel;
  filterModel?: GridFilterModel;
  quickFilterValues?: unknown[];
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
    if (!item.field) continue;
    const operator = operatorMap[item.operator] ?? item.operator;
    if (!hasFilterValue(item.operator, item.value)) continue;
    const value = item.operator === "isEmpty" || item.operator === "isNotEmpty" ? "true" : String(item.value);
    params.set(`filter[${item.field}][${operator}]`, value);
  }

  return params;
}

/** Return the backend operator name for a DataGrid operator. */
export function mapGridOperator(operator: string): string {
  return operatorMap[operator] ?? operator;
}
