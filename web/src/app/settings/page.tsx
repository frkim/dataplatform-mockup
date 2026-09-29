"use client";

import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SaveIcon from "@mui/icons-material/Save";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { CopyButton } from "@/components/CopyButton";
import { LoadingState } from "@/components/StateViews";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { AgentInfo, Page, PlatformInfo, PlatformSettings, WarehouseSize } from "@/lib/api-types";

const warehouseSizes: WarehouseSize[] = ["X-Small", "Small", "Medium", "Large", "X-Large"];
const validateRange = (value: number, min: number, max: number) =>
  Number.isInteger(value) && value >= min && value <= max;

/** Settings page for platform configuration and connection snippets. */
export default function SettingsPage() {
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [initial, setInitial] = useState<PlatformSettings | null>(null);
  const [platform, setPlatform] = useState<PlatformInfo | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      apiFetch<PlatformSettings>("/api/v1/settings"),
      apiFetch<PlatformInfo>("/api/v1/platform"),
      apiFetch<Page<AgentInfo>>("/api/v1/agents", { query: { pageSize: 100 } }),
    ]).then((results) => {
      if (!active) return;
      const [settingsResult, platformResult, agentsResult] = results;
      if (settingsResult.status === "fulfilled") {
        setSettings(settingsResult.value);
        setInitial(settingsResult.value);
      }
      if (platformResult.status === "fulfilled") setPlatform(platformResult.value);
      if (agentsResult.status === "fulfilled") setAgents(agentsResult.value.items);
      const rejected = results.find((result) => result.status === "rejected");
      if (rejected?.status === "rejected") {
        const reason = rejected.reason;
        setError(reason instanceof ApiError ? (reason.detail ?? reason.message) : "Unable to load settings.");
      }
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const errors = useMemo(() => {
    if (!settings) return {};
    return {
      workspaceName: settings.workspaceName.trim() ? "" : "Workspace name is required.",
      defaultPageSize: validateRange(settings.defaultPageSize, 1, 100) ? "" : "Must be an integer from 1 to 100.",
      maxQueryRows: validateRange(settings.maxQueryRows, 1, 10000) ? "" : "Must be an integer from 1 to 10000.",
      simulatedLatencyMs: validateRange(settings.simulatedLatencyMs, 0, 5000)
        ? ""
        : "Must be an integer from 0 to 5000.",
    };
  }, [settings]);
  const hasErrors = Object.values(errors).some(Boolean);

  const update = <K extends keyof PlatformSettings>(key: K, value: PlatformSettings[K]) => {
    setSettings((current) => (current ? { ...current, [key]: value } : current));
  };

  const save = async () => {
    if (!settings || hasErrors) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await apiFetch<PlatformSettings>("/api/v1/settings", { method: "PUT", body: settings });
      setSettings(updated);
      setInitial(updated);
      setSuccess(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Unable to save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState label="Loading settings" />;
  if (!settings) return <Alert severity="error">Settings are unavailable.</Alert>;

  const mcpSnippet = JSON.stringify(
    { servers: { dataplatform: { type: "http", url: platform?.endpoints.mcp ?? "http://localhost:8000/mcp" } } },
    null,
    2,
  );

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Settings
        </Typography>
        <Typography color="text.secondary">Configure the mock platform and copy MCP/A2A connection details.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack spacing={2}>
              <TextField
                label="Workspace name"
                value={settings.workspaceName}
                error={Boolean(errors.workspaceName)}
                helperText={errors.workspaceName}
                onChange={(event) => update("workspaceName", event.target.value)}
                fullWidth
              />
              <FormControl fullWidth>
                <InputLabel id="warehouse-size-label">Warehouse size</InputLabel>
                <Select
                  labelId="warehouse-size-label"
                  label="Warehouse size"
                  value={settings.warehouseSize}
                  onChange={(event) => update("warehouseSize", event.target.value as WarehouseSize)}
                >
                  {warehouseSizes.map((size) => (
                    <MenuItem key={size} value={size}>
                      {size}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    label="Default page size"
                    type="number"
                    value={settings.defaultPageSize}
                    error={Boolean(errors.defaultPageSize)}
                    helperText={errors.defaultPageSize}
                    onChange={(event) => update("defaultPageSize", Number(event.target.value))}
                    fullWidth
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    label="Max query rows"
                    type="number"
                    value={settings.maxQueryRows}
                    error={Boolean(errors.maxQueryRows)}
                    helperText={errors.maxQueryRows}
                    onChange={(event) => update("maxQueryRows", Number(event.target.value))}
                    fullWidth
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    label="Simulated latency (ms)"
                    type="number"
                    value={settings.simulatedLatencyMs}
                    error={Boolean(errors.simulatedLatencyMs)}
                    helperText={errors.simulatedLatencyMs}
                    onChange={(event) => update("simulatedLatencyMs", Number(event.target.value))}
                    fullWidth
                  />
                </Grid>
              </Grid>
              <Divider />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.mcpEnabled}
                    onChange={(event) => update("mcpEnabled", event.target.checked)}
                  />
                }
                label="MCP enabled"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.a2aEnabled}
                    onChange={(event) => update("a2aEnabled", event.target.checked)}
                  />
                }
                label="A2A enabled"
              />
              <Typography variant="subtitle1">Agents</Typography>
              {agents.map((agent) => (
                <FormControlLabel
                  key={agent.id}
                  control={
                    <Switch
                      checked={settings.agentsEnabled[agent.id] ?? agent.enabled}
                      onChange={(event) =>
                        update("agentsEnabled", { ...settings.agentsEnabled, [agent.id]: event.target.checked })
                      }
                    />
                  }
                  label={`${agent.name} (${agent.domain})`}
                />
              ))}
              <Stack direction="row" spacing={1}>
                <Button variant="contained" startIcon={<SaveIcon />} onClick={save} disabled={saving || hasErrors}>
                  {saving ? "Saving…" : "Save"}
                </Button>
                <Button
                  startIcon={<RestartAltIcon />}
                  onClick={() => setSettings(initial)}
                  disabled={!initial || saving}
                >
                  Reset
                </Button>
              </Stack>
            </Stack>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h6">Connections</Typography>
                <Box>
                  <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
                    <Typography variant="subtitle2">VS Code .vscode/mcp.json</Typography>
                    <CopyButton value={mcpSnippet} label="Copy MCP config" />
                  </Stack>
                  <Box component="pre" sx={{ overflow: "auto", p: 1.5, borderRadius: 2, bgcolor: "action.hover" }}>
                    <code>{mcpSnippet}</code>
                  </Box>
                </Box>
                <Divider />
                <Typography variant="subtitle2">A2A agent cards</Typography>
                {agents.map((agent) => (
                  <Stack key={agent.id} direction="row" spacing={1} sx={{ minWidth: 0, alignItems: "center" }}>
                    <Typography variant="body2" sx={{ flexGrow: 1, overflowWrap: "anywhere" }}>
                      {agent.name}: {agent.a2aCardUrl}
                    </Typography>
                    <CopyButton value={agent.a2aCardUrl} label={`Copy ${agent.name} A2A card URL`} />
                  </Stack>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Snackbar open={success} autoHideDuration={2500} onClose={() => setSuccess(false)} message="Settings saved" />
    </Stack>
  );
}
