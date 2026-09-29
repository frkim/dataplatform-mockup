"use client";

import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Divider,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { useEffect, useMemo, useState } from "react";
import { CopyButton } from "@/components/CopyButton";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { EmptyState, LoadingState } from "@/components/StateViews";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { AgentInfo, AgentReply, Page } from "@/lib/api-types";
import { dataGridType, formatGridValue } from "@/lib/format";

type ChatMessage = { id: string; role: "user" | "agent"; content: string; reply?: AgentReply };

/** AI agents page with cards and an invocation chat panel. */
export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<Page<AgentInfo>>("/api/v1/agents", { query: { pageSize: 100 } })
      .then((page) => {
        if (!active) return;
        setAgents(page.items);
        setSelectedId(page.items[0]?.id ?? null);
      })
      .catch(
        (caught) =>
          active && setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Unable to load agents."),
      )
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const selected = agents.find((agent) => agent.id === selectedId) ?? null;

  const sendMessage = async () => {
    if (!selected || !message.trim()) return;
    const prompt = message.trim();
    setMessage("");
    setSending(true);
    setError(null);
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: prompt }]);
    try {
      const reply = await apiFetch<AgentReply>(`/api/v1/agents/${encodeURIComponent(selected.id)}/invoke`, {
        method: "POST",
        body: { message: prompt },
      });
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "agent", content: reply.answer, reply }]);
    } catch (caught) {
      setError(caught instanceof ApiError ? (caught.detail ?? caught.message) : "Agent invocation failed.");
    } finally {
      setSending(false);
    }
  };

  const latestReply = [...messages].reverse().find((item) => item.reply)?.reply;
  const replyColumns = useMemo<GridColDef[]>(
    () =>
      latestReply?.columns.map((column) => {
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
    [latestReply],
  );
  const replyRows = useMemo(() => latestReply?.rows.map((row, index) => ({ id: index, ...row })) ?? [], [latestReply]);

  if (loading) return <LoadingState label="Loading agents" />;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          AI Agents
        </Typography>
        <Typography color="text.secondary">
          Invoke domain-specific agents and inspect generated SQL and result rows.
        </Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      {agents.length ? (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 5 }}>
            <Stack spacing={2}>
              {agents.map((agent) => (
                <Card
                  key={agent.id}
                  variant="outlined"
                  onClick={() => setSelectedId(agent.id)}
                  sx={{ cursor: "pointer", borderColor: selectedId === agent.id ? "primary.main" : "divider" }}
                >
                  <CardContent>
                    <Stack spacing={1.5}>
                      <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between" }}>
                        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                          <SmartToyIcon color="primary" />
                          <Typography variant="h6">{agent.name}</Typography>
                        </Stack>
                        <Chip
                          label={agent.enabled ? "Enabled" : "Disabled"}
                          color={agent.enabled ? "success" : "default"}
                          size="small"
                        />
                      </Stack>
                      <Typography color="text.secondary">{agent.domain}</Typography>
                      <Typography variant="body2">{agent.description}</Typography>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: "anywhere" }}>
                          {agent.a2aCardUrl}
                        </Typography>
                        <CopyButton value={agent.a2aCardUrl} label={`Copy ${agent.name} A2A card URL`} />
                      </Stack>
                      {agent.skills.map((skill) => (
                        <Box key={skill.id}>
                          <Typography variant="subtitle2">{skill.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {skill.description}
                          </Typography>
                          <Stack direction="row" spacing={1} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>
                            {skill.examples.map((example) => (
                              <Chip
                                key={example}
                                label={example}
                                size="small"
                                onClick={() => setMessage(example)}
                                clickable
                              />
                            ))}
                          </Stack>
                        </Box>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          </Grid>
          <Grid size={{ xs: 12, lg: 7 }}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="h6">Chat with {selected?.name ?? "agent"}</Typography>
                  <Typography color="text.secondary" variant="body2">
                    Messages are sent to the selected agent endpoint.
                  </Typography>
                </Box>
                <Divider />
                <Stack spacing={1.5} sx={{ maxHeight: 460, overflow: "auto" }} aria-live="polite">
                  {!messages.length && <EmptyState message="Choose an example prompt or type a message." />}
                  {messages.map((item) => (
                    <Paper
                      key={item.id}
                      variant="outlined"
                      sx={{ p: 1.5, alignSelf: item.role === "user" ? "flex-end" : "stretch", maxWidth: "100%" }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {item.role === "user" ? "You" : (selected?.name ?? "Agent")}
                      </Typography>
                      {item.role === "agent" ? (
                        <MarkdownRenderer markdown={item.content} />
                      ) : (
                        <Typography>{item.content}</Typography>
                      )}
                      {item.reply?.sql && (
                        <Collapse in>
                          <Box
                            component="pre"
                            sx={{ overflow: "auto", p: 1.5, borderRadius: 2, bgcolor: "action.hover" }}
                          >
                            <code>{item.reply.sql}</code>
                          </Box>
                        </Collapse>
                      )}
                    </Paper>
                  ))}
                </Stack>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                  <TextField
                    label="Message"
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    fullWidth
                    disabled={!selected || sending}
                    onKeyDown={(event) => {
                      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void sendMessage();
                    }}
                  />
                  <Button
                    variant="contained"
                    endIcon={<SendIcon />}
                    onClick={sendMessage}
                    disabled={!selected || sending || !message.trim()}
                  >
                    {sending ? "Sending…" : "Send"}
                  </Button>
                </Stack>
                {replyRows.length > 0 && (
                  <DataGrid
                    autoHeight
                    rows={replyRows}
                    columns={replyColumns}
                    density="compact"
                    pageSizeOptions={[5, 10, 25]}
                    disableRowSelectionOnClick
                  />
                )}
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      ) : (
        <EmptyState message="No agents are available." />
      )}
    </Stack>
  );
}
