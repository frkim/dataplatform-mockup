import type { ProblemDetails } from "./api-types";

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  query?: URLSearchParams | Record<string, string | number | boolean | undefined>;
};

/** Error thrown for RFC 9457 problem+json and failed network responses. */
export class ApiError extends Error {
  readonly status?: number;
  readonly title: string;
  readonly detail?: string;
  readonly problem?: ProblemDetails;

  constructor(
    message: string,
    options: { status?: number; title?: string; detail?: string; problem?: ProblemDetails } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.title = options.title ?? message;
    this.detail = options.detail;
    this.problem = options.problem;
  }
}

const buildUrl = (path: string, query?: ApiRequestOptions["query"]) => {
  const params = query instanceof URLSearchParams ? query : new URLSearchParams();
  if (query && !(query instanceof URLSearchParams)) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) params.set(key, String(value));
    }
  }
  const search = params.toString();
  return search ? `${path}?${search}` : path;
};

/** Fetch JSON from the platform API and throw ApiError for problem responses. */
export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, query, headers, ...init } = options;
  const requestHeaders = new Headers(headers);
  if (body !== undefined && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }
  requestHeaders.set("Accept", "application/json, application/problem+json");

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      ...init,
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: requestHeaders,
    });
  } catch (error) {
    throw new ApiError("Network error", { detail: error instanceof Error ? error.message : String(error) });
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("json");
  const payload = isJson ? await response.json().catch(() => undefined) : await response.text().catch(() => undefined);

  if (!response.ok) {
    if (contentType.includes("application/problem+json") && payload && typeof payload === "object") {
      const problem = payload as ProblemDetails;
      throw new ApiError(problem.detail ?? problem.title, {
        status: problem.status,
        title: problem.title,
        detail: problem.detail,
        problem,
      });
    }
    throw new ApiError(response.statusText || "Request failed", {
      status: response.status,
      title: response.statusText,
    });
  }

  return payload as T;
}
