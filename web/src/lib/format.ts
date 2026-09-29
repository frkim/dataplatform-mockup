const ungroupedNumericColumnPattern = /(^id$|_id$|year$)/i;

/** Format a number for compact dashboard display. */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat(undefined, { notation: value >= 10000 ? "compact" : "standard" }).format(value);
}

/** Map backend SQL types into MUI DataGrid column types. */
export function dataGridType(duckType: string): "string" | "number" | "date" | "dateTime" | "boolean" {
  const type = duckType.toUpperCase();
  if (type.includes("BOOL")) return "boolean";
  if (type.includes("TIMESTAMP")) return "dateTime";
  if (type === "DATE") return "date";
  if (["INT", "BIGINT", "DOUBLE", "FLOAT", "REAL", "DECIMAL", "NUMERIC"].some((token) => type.includes(token)))
    return "number";
  return "string";
}

/** Return whether a numeric column should render without thousands grouping. */
export function shouldDisableNumberGrouping(field: string): boolean {
  return ungroupedNumericColumnPattern.test(field);
}

/** Format DataGrid cell values while keeping id/year-like numbers ungrouped. */
export function formatGridValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value !== "number") return String(value);
  if (shouldDisableNumberGrouping(field)) return String(value);
  return new Intl.NumberFormat().format(value);
}
