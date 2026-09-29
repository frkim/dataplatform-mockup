"use client";

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { Alert, Box, Button, Chip, Paper, Stack, TextField, Typography } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { useCallback, useMemo, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { QueryResult } from "@/lib/api-types";
import { dataGridType, formatGridValue } from "@/lib/format";

const samples = [
  "SELECT * FROM manufacturing.production.plants LIMIT 25",
  "SELECT status, count(*) AS orders FROM retail.sales.orders GROUP BY status ORDER BY orders DESC",
  "SELECT strftime(order_date, '%Y-%m') AS month, round(sum(total_amount), 2) AS revenue FROM retail.sales.orders WHERE status <> 'cancelled' GROUP BY 1 ORDER BY 1",
];

/** SQL worksheet page for running read-only platform queries. */
export default function SqlPage() {
  const [sql, setSql] = useState(samples[2]);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runQuery = useCallback(async () => {
    if (!sql.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(
        await apiFetch<QueryResult>("/api/v1/query", {
          method: "POST",
          headers: { "X-Query-Source": "ui" },
          body: { sql, maxRows: 1000 },
        }),
      );
    } catch (caught) {
      setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Query failed.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [sql]);

  const columns = useMemo<GridColDef[]>(
    () =>
      result?.columns.map((column) => {
        const gridType = dataGridType(column.type);
        return {
          field: column.name,
          headerName: column.name,
          flex: 1,
          minWidth: 140,
          type: gridType,
          valueFormatter: gridType === "number" ? (value: unknown) => formatGridValue(column.name, value) : undefined,
        };
      }) ?? [],
    [result],
  );
  const rows = useMemo(() => result?.rows.map((row, index) => ({ id: index, ...row })) ?? [], [result]);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          SQL Worksheet
        </Typography>
        <Typography color="text.secondary">
          Run read-only SELECT/WITH statements against the mock data platform.
        </Typography>
      </Box>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={2}>
          <TextField
            label="SQL query"
            value={sql}
            onChange={(event) => setSql(event.target.value)}
            multiline
            minRows={8}
            fullWidth
            sx={{ "& textarea": { fontFamily: "monospace" } }}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.preventDefault();
                void runQuery();
              }
            }}
          />
          <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
            {samples.map((sample) => (
              <Chip key={sample} label={sample.slice(0, 54)} onClick={() => setSql(sample)} clickable />
            ))}
          </Stack>
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={runQuery}
            disabled={loading || !sql.trim()}
          >
            {loading ? "Running…" : "Run query"}
          </Button>
        </Stack>
      </Paper>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }} useFlexGap>
          {result && (
            <>
              <Chip label={`${result.rowCount} rows`} />
              <Chip label={`${result.durationMs} ms`} />
              {result.truncated && <Chip color="warning" label="Truncated" />}
            </>
          )}
        </Stack>
        <DataGrid
          autoHeight
          loading={loading}
          rows={rows}
          columns={columns}
          pageSizeOptions={[10, 25, 50, 100]}
          initialState={{ pagination: { paginationModel: { page: 0, pageSize: 25 } } }}
          disableRowSelectionOnClick
          showToolbar
          slotProps={{ toolbar: { showQuickFilter: true } }}
          localeText={{ noRowsLabel: result ? "No rows returned." : "Run a query to see results." }}
        />
      </Paper>
    </Stack>
  );
}
