import { describe, expect, it } from "vitest";
import { sqlColumnDef } from "./grid-columns";

describe("sqlColumnDef", () => {
  it("converts DATE and TIMESTAMP strings into Date objects for the grid", () => {
    const date = sqlColumnDef({ name: "install_date", type: "DATE" });
    const timestamp = sqlColumnDef({ name: "reading_at", type: "TIMESTAMP" });
    expect(date.type).toBe("date");
    expect(timestamp.type).toBe("dateTime");
    const getDate = date.valueGetter as unknown as (value: unknown) => Date | null;
    const getTimestamp = timestamp.valueGetter as unknown as (value: unknown) => Date | null;
    expect(getDate("2024-03-05")).toBeInstanceOf(Date);
    expect(getTimestamp("2026-06-01T08:30:00")?.getHours()).toBe(8);
    expect(getDate(null)).toBeNull();
  });

  it("offers only backend-supported filter operators for server-side filtering", () => {
    const text = sqlColumnDef({ name: "name", type: "VARCHAR" }, { serverFiltering: true });
    const number = sqlColumnDef({ name: "qty", type: "INTEGER" }, { serverFiltering: true });
    expect(text.filterOperators?.map((op) => op.value)).toEqual([
      "contains",
      "equals",
      "startsWith",
      "endsWith",
      "isEmpty",
      "isNotEmpty",
    ]);
    expect(number.filterOperators?.map((op) => op.value)).not.toContain("isAnyOf");
    expect(sqlColumnDef({ name: "name", type: "VARCHAR" }).filterOperators).toBeUndefined();
  });

  it("formats numbers and keeps the column description", () => {
    const column = sqlColumnDef({ name: "revenue", type: "DOUBLE", description: "Net revenue" });
    expect(column.description).toBe("Net revenue");
    const format = column.valueFormatter as unknown as (value: unknown) => string;
    expect(format(1234567)).toBe(new Intl.NumberFormat().format(1234567));
  });
});
