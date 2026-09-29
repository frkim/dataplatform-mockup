"use client";

import PsychologyIcon from "@mui/icons-material/Psychology";
import StorageIcon from "@mui/icons-material/Storage";
import TableChartIcon from "@mui/icons-material/TableChart";
import ViewModuleIcon from "@mui/icons-material/ViewModule";
import { Alert, Box, Card, CardContent, Chip, Grid, Paper, Stack, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { CopyButton } from "@/components/CopyButton";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { RevenueChart } from "@/components/RevenueChart";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { AgentInfo, Page, PlatformInfo, QueryResult } from "@/lib/api-types";
import { formatNumber } from "@/lib/format";

const dashboardSql =
  "SELECT strftime(order_date, '%Y-%m') AS month, round(sum(total_amount), 2) AS revenue FROM retail.sales.orders WHERE status <> 'cancelled' GROUP BY 1 ORDER BY 1";

const statIcons = [StorageIcon, ViewModuleIcon, TableChartIcon, TableChartIcon];

/** Dashboard landing page with platform stats, endpoints, chart, and agent summary. */
export default function DashboardPage() {
  const [platform, setPlatform] = useState<PlatformInfo | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [query, setQuery] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      apiFetch<PlatformInfo>("/api/v1/platform"),
      apiFetch<Page<AgentInfo>>("/api/v1/agents", { query: { pageSize: 100 } }),
      apiFetch<QueryResult>("/api/v1/query", {
        method: "POST",
        headers: { "X-Query-Source": "ui" },
        body: { sql: dashboardSql, maxRows: 48 },
      }),
    ]).then((results) => {
      if (!active) return;
      const [platformResult, agentsResult, queryResult] = results;
      if (platformResult.status === "fulfilled") setPlatform(platformResult.value);
      if (agentsResult.status === "fulfilled") setAgents(agentsResult.value.items);
      if (queryResult.status === "fulfilled") setQuery(queryResult.value);
      const rejected = results.find((result) => result.status === "rejected");
      if (rejected?.status === "rejected") {
        const reason = rejected.reason;
        setError(reason instanceof ApiError ? (reason.detail ?? reason.message) : "Unable to load dashboard data.");
      }
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const revenue = useMemo(
    () =>
      query?.rows
        .map((row) => ({ month: String(row.month ?? ""), revenue: Number(row.revenue ?? 0) }))
        .filter((row) => row.month) ?? [],
    [query],
  );

  if (loading) return <LoadingState label="Loading dashboard" />;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Dashboard
        </Typography>
        <Typography color="text.secondary">Synthetic manufacturing and retail data platform console.</Typography>
      </Box>
      {error && <Alert severity="warning">{error}</Alert>}
      {platform ? (
        <Grid container spacing={2}>
          {[
            ["Catalogs", platform.stats.catalogs],
            ["Schemas", platform.stats.schemas],
            ["Tables", platform.stats.tables],
            ["Rows", platform.stats.totalRows],
          ].map(([label, value], index) => {
            const Icon = statIcons[index];
            return (
              <Grid key={label} size={{ xs: 12, sm: 6, lg: 3 }}>
                <Card variant="outlined">
                  <CardContent>
                    <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                      <Icon color="primary" fontSize="large" />
                      <Box>
                        <Typography color="text.secondary" variant="body2">
                          {label}
                        </Typography>
                        <Typography variant="h4">{formatNumber(Number(value))}</Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      ) : (
        <ErrorState message="Platform metadata is unavailable." />
      )}

      {platform && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Connection endpoints
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(platform.endpoints).map(([name, value]) => (
              <Grid key={name} size={{ xs: 12, md: 6 }}>
                <Stack direction="row" spacing={1} sx={{ minWidth: 0, alignItems: "center" }}>
                  <Chip label={name.toUpperCase()} size="small" color="secondary" />
                  <Typography variant="body2" sx={{ overflowWrap: "anywhere", flexGrow: 1 }}>
                    {value}
                  </Typography>
                  <CopyButton value={value} label={`Copy ${name} endpoint`} />
                </Stack>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      <RevenueChart data={revenue} />

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} sx={{ mb: 2, alignItems: "center" }}>
          <PsychologyIcon color="primary" />
          <Typography variant="h6">AI agents</Typography>
        </Stack>
        {agents.length ? (
          <Grid container spacing={2}>
            {agents.map((agent) => (
              <Grid key={agent.id} size={{ xs: 12, md: 6, xl: 3 }}>
                <Card variant="outlined">
                  <CardContent>
                    <Stack spacing={1}>
                      <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between" }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                          {agent.name}
                        </Typography>
                        <Chip
                          label={agent.enabled ? "Enabled" : "Disabled"}
                          color={agent.enabled ? "success" : "default"}
                          size="small"
                        />
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {agent.domain}
                      </Typography>
                      <Typography variant="body2">{agent.description}</Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : (
          <EmptyState message="No agents returned by the platform." />
        )}
      </Paper>
    </Stack>
  );
}
