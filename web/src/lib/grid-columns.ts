import {
  getGridBooleanOperators,
  getGridDateOperators,
  getGridNumericOperators,
  getGridStringOperators,
  type GridColDef,
  type GridFilterOperator,
} from "@mui/x-data-grid";
import { dataGridType, formatGridValue, parseSqlDate } from "./format";
import { isSupportedGridOperator } from "./grid-query";

export type SqlColumn = { name: string; type: string; description?: string | null };

type ColumnOptions = {
  /** Only offer filter operators the REST API understands (for server-side filtering). */
  serverFiltering?: boolean;
  minWidth?: number;
};

function defaultOperators(type: ReturnType<typeof dataGridType>): GridFilterOperator[] {
  switch (type) {
    case "number":
      return getGridNumericOperators();
    case "date":
      return getGridDateOperators(false);
    case "dateTime":
      return getGridDateOperators(true);
    case "boolean":
      return getGridBooleanOperators();
    default:
      return getGridStringOperators();
  }
}

/**
 * Build a DataGrid column for a SQL result column. Date/timestamp values arrive as ISO strings, and the
 * DataGrid `date`/`dateTime` types require `Date` objects, so they are parsed with a `valueGetter`.
 */
export function sqlColumnDef(column: SqlColumn, { serverFiltering = false, minWidth = 140 }: ColumnOptions = {}) {
  const type = dataGridType(column.type);
  const def: GridColDef = {
    field: column.name,
    headerName: column.name,
    flex: 1,
    minWidth,
    type,
  };
  if (column.description) def.description = column.description;
  if (type === "number") def.valueFormatter = (value: unknown) => formatGridValue(column.name, value);
  if (type === "date" || type === "dateTime") def.valueGetter = (value: unknown) => parseSqlDate(value);
  if (serverFiltering) {
    def.filterOperators = defaultOperators(type).filter((operator) => isSupportedGridOperator(operator.value));
  }
  return def;
}
