import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, ApiError } from "./api-client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("apiFetch", () => {
  it("returns successful JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }),
        ),
    );
    await expect(apiFetch<{ ok: boolean }>("/api/v1/platform")).resolves.toEqual({ ok: true });
  });

  it("throws ApiError for problem+json", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ title: "Bad SQL", detail: "Only SELECT is allowed", status: 400 }), {
          status: 400,
          headers: { "content-type": "application/problem+json" },
        }),
      ),
    );
    await expect(apiFetch("/api/v1/query")).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      title: "Bad SQL",
      detail: "Only SELECT is allowed",
    });
  });

  it("wraps network errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection refused")));
    await expect(apiFetch("/api/v1/platform")).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch("/api/v1/platform")).rejects.toMatchObject({ title: "Network error" });
  });
});
