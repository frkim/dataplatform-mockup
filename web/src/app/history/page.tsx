"use client";

import { Alert, Box, Chip, Paper, Stack, TextField, Typography } from "@mui/material";
import {
  DataGrid,
  type GridColDef,
  type GridFilterModel,
  type GridPaginationModel,
  type GridSortModel,
} from "@mui/x-data-grid";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Page, QueryHistoryEntry } from "@/lib/api-types";
import { buildGridQuery } from "@/lib/grid-query";

/** Query history page with a server-side DataGrid. */
export default function HistoryPage() {
  const [rows, setRows] = useState<QueryHistoryEntry[]>([]);
  const [rowCount, setRowCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: "startedAt", sort: "desc" }]);
  const [filterModel, setFilterModel] = useState<GridFilterModel>({ items: [] });
  const [quick, setQuick] = useState("");
  const [debouncedQuick, setDebouncedQuick] = useState("");

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQuick(quick), 300);
    return () => window.clearTimeout(id);
  }, [quick]);

  const loadRows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = buildGridQuery({
        paginationModel,
        sortModel,
        filterModel: { ...filterModel, quickFilterValues: debouncedQuick ? [debouncedQuick] : [] },
      });
      const page = await apiFetch<Page<QueryHistoryEntry>>("/api/v1/queries", { query: params });
      setRows(page.items);
      setRowCount(page.total);
    } catch (caught) {
      setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Unable to load query history.");
      setRows([]);
      setRowCount(0);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuick, filterModel, paginationModel, sortModel]);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  const columns = useMemo<GridColDef<QueryHistoryEntry>[]>(
    () => [
      {
        field: "startedAt",
        headerName: "Started",
        type: "dateTime",
        minWidth: 190,
        valueGetter: (value) => new Date(String(value)),
      },
      {
        field: "status",
        headerName: "Status",
        width: 140,
        renderCell: ({ value }) => (
          <Chip label={value} color={value === "succeeded" ? "success" : "error"} size="small" />
        ),
      },
      {
        field: "source",
        headerName: "Source",
        width: 120,
        renderCell: ({ value }) => <Chip label={value} size="small" />,
      },
      { field: "rowCount", headerName: "Rows", type: "number", width: 110 },
      { field: "durationMs", headerName: "Duration (ms)", type: "number", width: 150 },
      { field: "sql", headerName: "SQL", flex: 1, minWidth: 320 },
      { field: "error", headerName: "Error", flex: 1, minWidth: 220 },
    ],
    [],
  );

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Query History
        </Typography>
        <Typography color="text.secondary">Audit queries from the UI, APIs, MCP, A2A, and agents.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={2}>
          <TextField
            label="Global search"
            value={quick}
            onChange={(event) => {
              setQuick(event.target.value);
              setPaginationModel((current) => ({ ...current, page: 0 }));
            }}
            fullWidth
          />
          <DataGrid
            autoHeight
            getRowId={(row) => row.id}
            rows={rows}
            columns={columns}
            rowCount={rowCount}
            loading={loading}
            paginationMode="server"
            sortingMode="server"
            filterMode="server"
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            sortModel={sortModel}
            onSortModelChange={setSortModel}
            filterModel={filterModel}
            onFilterModelChange={(model) => {
              setFilterModel(model);
              setPaginationModel((current) => ({ ...current, page: 0 }));
            }}
            pageSizeOptions={[10, 25, 50, 100]}
            disableRowSelectionOnClick
            localeText={{ noRowsLabel: loading ? "Loading history…" : "No query history found." }}
          />
        </Stack>
      </Paper>
    </Stack>
  );
}
