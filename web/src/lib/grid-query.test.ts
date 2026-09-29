import { describe, expect, it } from "vitest";
import { buildGridQuery, mapGridOperator } from "./grid-query";

describe("buildGridQuery", () => {
  it("converts zero-based pagination to one-based backend params", () => {
    const params = buildGridQuery({ paginationModel: { page: 2, pageSize: 50 } });
    expect(params.get("page")).toBe("3");
    expect(params.get("pageSize")).toBe("50");
  });

  it("uses the first active sort item", () => {
    const params = buildGridQuery({ sortModel: [{ field: "startedAt", sort: "desc" }] });
    expect(params.get("sort")).toBe("startedAt");
    expect(params.get("order")).toBe("desc");
  });

  it("maps quick filter values to q", () => {
    const params = buildGridQuery({ filterModel: { items: [], quickFilterValues: ["plant", "north"] } });
    expect(params.get("q")).toBe("plant north");
  });

  it.each([
    ["contains", "contains"],
    ["equals", "equals"],
    ["startsWith", "startsWith"],
    ["endsWith", "endsWith"],
    ["isEmpty", "isEmpty"],
    ["isNotEmpty", "isNotEmpty"],
    ["=", "eq"],
    ["!=", "neq"],
    [">", "gt"],
    [">=", "gte"],
    ["<", "lt"],
    ["<=", "lte"],
    ["is", "eq"],
    ["not", "neq"],
    ["after", "gt"],
    ["onOrAfter", "gte"],
    ["before", "lt"],
    ["onOrBefore", "lte"],
  ])("maps %s to %s", (muiOperator, apiOperator) => {
    expect(mapGridOperator(muiOperator)).toBe(apiOperator);
    const params = buildGridQuery({ filterModel: { items: [{ field: "col", operator: muiOperator, value: "42" }] } });
    const expectedValue = muiOperator === "isEmpty" || muiOperator === "isNotEmpty" ? "true" : "42";
    expect(params.get(`filter[col][${apiOperator}]`)).toBe(expectedValue);
  });

  it("passes a sentinel value for empty checks", () => {
    const params = buildGridQuery({ filterModel: { items: [{ field: "description", operator: "isEmpty" }] } });
    expect(params.get("filter[description][isEmpty]")).toBe("true");
  });

  it("skips filters without values except empty checks", () => {
    const params = buildGridQuery({
      filterModel: {
        items: [
          { field: "name", operator: "contains", value: "" },
          { field: "count", operator: ">", value: undefined },
          { field: "description", operator: "isNotEmpty" },
        ],
      },
    });
    expect(params.has("filter[name][contains]")).toBe(false);
    expect(params.has("filter[count][gt]")).toBe(false);
    expect(params.get("filter[description][isNotEmpty]")).toBe("true");
  });
});
