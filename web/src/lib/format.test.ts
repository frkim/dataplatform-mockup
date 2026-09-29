import { describe, expect, it } from "vitest";
import { formatGridValue, shouldDisableNumberGrouping } from "./format";

describe("formatGridValue", () => {
  it("does not group year-like or id-like numeric columns", () => {
    expect(shouldDisableNumberGrouping("opened_year")).toBe(true);
    expect(shouldDisableNumberGrouping("store_id")).toBe(true);
    expect(shouldDisableNumberGrouping("id")).toBe(true);
    expect(formatGridValue("opened_year", 1998)).toBe("1998");
    expect(formatGridValue("store_id", 120045)).toBe("120045");
  });

  it("groups ordinary numeric columns", () => {
    expect(shouldDisableNumberGrouping("row_count")).toBe(false);
    expect(formatGridValue("row_count", 120045)).toBe("120,045");
  });
});
