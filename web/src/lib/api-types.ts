export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
};

export type ProblemDetails = {
  type?: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  traceId?: string;
};

export type PlatformInfo = {
  name: string;
  version: string;
  workspaceName: string;
  engine: string;
  endpoints: { rest: string; mcp: string; a2a: string; openapi: string };
  stats: { catalogs: number; schemas: number; tables: number; totalRows: number };
};

export type Catalog = { name: string; description: string; schemaCount: number };
export type Schema = { catalog: string; name: string; description: string; tableCount: number };
export type TableSummary = {
  catalog: string;
  schema: string;
  name: string;
  fullName: string;
  description: string;
  rowCount: number;
  columnCount: number;
};
export type Column = {
  name: string;
  type: string;
  description: string;
  nullable: boolean;
  primaryKey: boolean;
};
export type TableDetail = TableSummary & { columns: Column[] };

export type QueryColumn = { name: string; type: string };
export type QueryResult = {
  queryId: string;
  columns: QueryColumn[];
  rows: Record<string, unknown>[];
  rowCount: number;
  truncated: boolean;
  durationMs: number;
};
export type QueryHistoryEntry = {
  id: string;
  sql: string;
  source: "ui" | "api" | "mcp" | "a2a" | "agent";
  status: "succeeded" | "failed";
  rowCount: number;
  durationMs: number;
  error: string | null;
  startedAt: string;
};

export type AgentSkill = { id: string; name: string; description: string; examples: string[] };
export type AgentInfo = {
  id: string;
  name: string;
  description: string;
  domain: string;
  enabled: boolean;
  skills: AgentSkill[];
  a2aCardUrl: string;
};
export type AgentReply = {
  agentId: string;
  skillId: string;
  answer: string;
  sql: string | null;
  columns: QueryColumn[];
  rows: Record<string, unknown>[];
};

export type WarehouseSize = "X-Small" | "Small" | "Medium" | "Large" | "X-Large";
export type PlatformSettings = {
  workspaceName: string;
  warehouseSize: WarehouseSize;
  defaultPageSize: number;
  maxQueryRows: number;
  simulatedLatencyMs: number;
  mcpEnabled: boolean;
  a2aEnabled: boolean;
  agentsEnabled: Record<string, boolean>;
};
