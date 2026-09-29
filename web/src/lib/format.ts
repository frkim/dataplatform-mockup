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

const isoDatePattern = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * Parse an API date/timestamp value into a `Date` for DataGrid `date`/`dateTime` columns.
 * Plain `YYYY-MM-DD` values become local midnight (not UTC) so the displayed day never shifts.
 */
export function parseSqlDate(value: unknown): Date | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const text = String(value);
  const dateOnly = isoDatePattern.exec(text);
  const parsed = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(text);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
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
