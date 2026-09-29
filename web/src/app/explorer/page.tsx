"use client";

import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SearchIcon from "@mui/icons-material/Search";
import StorageIcon from "@mui/icons-material/Storage";
import TableRowsIcon from "@mui/icons-material/TableRows";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import {
  Alert,
  Box,
  Collapse,
  Divider,
  Grid,
  InputAdornment,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import {
  DataGrid,
  type GridColDef,
  type GridFilterModel,
  type GridPaginationModel,
  type GridSortModel,
} from "@mui/x-data-grid";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Catalog, Page, Schema, TableDetail, TableSummary } from "@/lib/api-types";
import { dataGridType, formatGridValue, formatNumber } from "@/lib/format";
import { buildGridQuery } from "@/lib/grid-query";

type CatalogNode = Catalog & { schemas: (Schema & { tables: TableSummary[] })[] };

const splitTableName = (fullName: string) => {
  const [catalog, schema, table] = fullName.split(".");
  return { catalog, schema, table };
};

/** Data Explorer page for browsing catalogs, schemas, tables, and row data. */
export default function ExplorerPage() {
  const [tree, setTree] = useState<CatalogNode[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [detail, setDetail] = useState<TableDetail | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [rowCount, setRowCount] = useState(0);
  const [loadingTree, setLoadingTree] = useState(true);
  const [loadingRows, setLoadingRows] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState(0);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const [filterModel, setFilterModel] = useState<GridFilterModel>({ items: [] });
  const [quick, setQuick] = useState("");
  const [debouncedQuick, setDebouncedQuick] = useState("");

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQuick(quick), 300);
    return () => window.clearTimeout(id);
  }, [quick]);

  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("table");
    if (initial) setSelectedTable(initial);
  }, []);

  useEffect(() => {
    let active = true;
    const loadTree = async () => {
      setLoadingTree(true);
      setError(null);
      try {
        const catalogs = await apiFetch<Page<Catalog>>("/api/v1/catalogs", { query: { pageSize: 100 } });
        const nodes = await Promise.all(
          catalogs.items.map(async (catalog) => {
            const schemas = await apiFetch<Page<Schema>>(
              `/api/v1/catalogs/${encodeURIComponent(catalog.name)}/schemas`,
              {
                query: { pageSize: 100 },
              },
            );
            const schemasWithTables = await Promise.all(
              schemas.items.map(async (schema) => {
                const tables = await apiFetch<Page<TableSummary>>(
                  `/api/v1/catalogs/${encodeURIComponent(catalog.name)}/schemas/${encodeURIComponent(schema.name)}/tables`,
                  { query: { pageSize: 100 } },
                );
                return { ...schema, tables: tables.items };
              }),
            );
            return { ...catalog, schemas: schemasWithTables };
          }),
        );
        if (!active) return;
        setTree(nodes);
        const firstTable = nodes.flatMap((catalog) => catalog.schemas.flatMap((schema) => schema.tables))[0];
        setSelectedTable((current) => current ?? firstTable?.fullName ?? null);
        const open = new Set<string>();
        nodes.forEach((catalog) => {
          open.add(catalog.name);
          catalog.schemas.forEach((schema) => open.add(`${catalog.name}.${schema.name}`));
        });
        setExpanded(open);
      } catch (caught) {
        if (active)
          setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Unable to load catalog tree.");
      } finally {
        if (active) setLoadingTree(false);
      }
    };
    void loadTree();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedTable) return;
    const { catalog, schema, table } = splitTableName(selectedTable);
    if (!catalog || !schema || !table) return;
    let active = true;
    setError(null);
    apiFetch<TableDetail>(
      `/api/v1/catalogs/${encodeURIComponent(catalog)}/schemas/${encodeURIComponent(schema)}/tables/${encodeURIComponent(table)}`,
    )
      .then((value) => {
        if (active) {
          setDetail(value);
          window.history.replaceState(null, "", `/explorer?table=${encodeURIComponent(value.fullName)}`);
        }
      })
      .catch(
        (caught) =>
          active && setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Unable to load table."),
      );
    return () => {
      active = false;
    };
  }, [selectedTable]);

  const loadRows = useCallback(async () => {
    if (!detail) return;
    setLoadingRows(true);
    setError(null);
    try {
      const params = buildGridQuery({
        paginationModel,
        sortModel,
        filterModel: { ...filterModel, quickFilterValues: debouncedQuick ? [debouncedQuick] : [] },
      });
      const page = await apiFetch<Page<Record<string, unknown>>>(
        `/api/v1/catalogs/${encodeURIComponent(detail.catalog)}/schemas/${encodeURIComponent(detail.schema)}/tables/${encodeURIComponent(detail.name)}/rows`,
        { query: params },
      );
      setRows(page.items.map((row, index) => ({ id: `${page.page}-${index}`, ...row })));
      setRowCount(page.total);
    } catch (caught) {
      setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Unable to load rows.");
      setRows([]);
      setRowCount(0);
    } finally {
      setLoadingRows(false);
    }
  }, [debouncedQuick, detail, filterModel, paginationModel, sortModel]);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  const columns = useMemo<GridColDef[]>(
    () =>
      detail?.columns.map((column) => {
        const gridType = dataGridType(column.type);
        return {
          field: column.name,
          headerName: column.name,
          flex: 1,
          minWidth: 150,
          type: gridType,
          description: column.description,
          valueFormatter: gridType === "number" ? (value: unknown) => formatGridValue(column.name, value) : undefined,
        };
      }) ?? [],
    [detail],
  );

  const schemaRows = useMemo(() => detail?.columns.map((column) => ({ id: column.name, ...column })) ?? [], [detail]);

  const toggleExpanded = (key: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Data Explorer
        </Typography>
        <Typography color="text.secondary">Browse catalogs, table schemas, and server-side filtered data.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4, lg: 3 }}>
          <Paper variant="outlined" sx={{ p: 1, minHeight: 520 }}>
            <Typography variant="h6" sx={{ p: 1 }}>
              Catalogs
            </Typography>
            <Divider />
            <List aria-label="Catalog tree" dense>
              {loadingTree && <ListItemText sx={{ p: 2 }} primary="Loading catalogs…" />}
              {!loadingTree && !tree.length && <ListItemText sx={{ p: 2 }} primary="No catalogs available." />}
              {tree.map((catalog) => (
                <Box key={catalog.name}>
                  <ListItemButton onClick={() => toggleExpanded(catalog.name)}>
                    <ListItemIcon>
                      <StorageIcon />
                    </ListItemIcon>
                    <ListItemText primary={catalog.name} secondary={`${catalog.schemaCount} schemas`} />
                    {expanded.has(catalog.name) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </ListItemButton>
                  <Collapse in={expanded.has(catalog.name)} timeout="auto" unmountOnExit>
                    <List dense component="div" disablePadding>
                      {catalog.schemas.map((schema) => {
                        const schemaKey = `${catalog.name}.${schema.name}`;
                        return (
                          <Box key={schemaKey}>
                            <ListItemButton sx={{ pl: 4 }} onClick={() => toggleExpanded(schemaKey)}>
                              <ListItemText primary={schema.name} secondary={`${schema.tableCount} tables`} />
                              {expanded.has(schemaKey) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            </ListItemButton>
                            <Collapse in={expanded.has(schemaKey)} timeout="auto" unmountOnExit>
                              <List dense component="div" disablePadding>
                                {schema.tables.map((table) => (
                                  <ListItemButton
                                    key={table.fullName}
                                    selected={selectedTable === table.fullName}
                                    sx={{ pl: 6 }}
                                    onClick={() => {
                                      setSelectedTable(table.fullName);
                                      setPaginationModel((current) => ({ ...current, page: 0 }));
                                    }}
                                  >
                                    <ListItemIcon>
                                      <TableRowsIcon fontSize="small" />
                                    </ListItemIcon>
                                    <ListItemText
                                      primary={table.name}
                                      secondary={`${formatNumber(table.rowCount)} rows`}
                                    />
                                  </ListItemButton>
                                ))}
                              </List>
                            </Collapse>
                          </Box>
                        );
                      })}
                    </List>
                  </Collapse>
                </Box>
              ))}
            </List>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 8, lg: 9 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            {detail ? (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="h5">{detail.fullName}</Typography>
                  <Typography color="text.secondary">{detail.description}</Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <ViewColumnIcon color="primary" />
                    <Typography variant="body2">
                      {formatNumber(detail.rowCount)} rows · {detail.columnCount} columns
                    </Typography>
                  </Stack>
                </Box>
                <Tabs value={tab} onChange={(_, value: number) => setTab(value)} aria-label="Explorer tabs">
                  <Tab label="Data" />
                  <Tab label="Schema" />
                </Tabs>
                {tab === 0 && (
                  <Stack spacing={2}>
                    <TextField
                      aria-label="Quick filter table rows"
                      placeholder="Quick filter"
                      size="small"
                      value={quick}
                      onChange={(event) => {
                        setQuick(event.target.value);
                        setPaginationModel((current) => ({ ...current, page: 0 }));
                      }}
                      slotProps={{
                        input: {
                          startAdornment: (
                            <InputAdornment position="start">
                              <SearchIcon fontSize="small" />
                            </InputAdornment>
                          ),
                        },
                      }}
                      fullWidth
                    />
                    <DataGrid
                      autoHeight
                      rows={rows}
                      columns={columns}
                      rowCount={rowCount}
                      loading={loadingRows}
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
                      localeText={{ noRowsLabel: loadingRows ? "Loading rows…" : "No rows match the current filters." }}
                    />
                  </Stack>
                )}
                {tab === 1 && (
                  <DataGrid
                    autoHeight
                    rows={schemaRows}
                    columns={[
                      { field: "name", headerName: "Name", flex: 1, minWidth: 160 },
                      { field: "type", headerName: "Type", width: 150 },
                      { field: "description", headerName: "Description", flex: 2, minWidth: 240 },
                      { field: "nullable", headerName: "Nullable", type: "boolean", width: 110 },
                      { field: "primaryKey", headerName: "Primary key", type: "boolean", width: 130 },
                    ]}
                    pageSizeOptions={[25, 50, 100]}
                    disableRowSelectionOnClick
                  />
                )}
              </Stack>
            ) : (
              <Typography color="text.secondary">Select a table to inspect its data and schema.</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Stack>
  );
}
