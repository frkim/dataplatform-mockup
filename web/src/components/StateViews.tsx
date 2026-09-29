import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import InboxIcon from "@mui/icons-material/Inbox";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

/** Show a centered loading indicator for data views. */
export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <Stack spacing={2} sx={{ minHeight: 180, alignItems: "center", justifyContent: "center" }}>
      <CircularProgress aria-label={label} />
      <Typography color="text.secondary">{label}…</Typography>
    </Stack>
  );
}

/** Show an empty state when a data view has no rows. */
export function EmptyState({ message = "No data available." }: { message?: string }) {
  return (
    <Stack spacing={1} sx={{ minHeight: 180, alignItems: "center", justifyContent: "center" }}>
      <InboxIcon color="disabled" />
      <Typography color="text.secondary">{message}</Typography>
    </Stack>
  );
}

/** Show an error alert for failed data views. */
export function ErrorState({ message }: { message: string }) {
  return (
    <Box sx={{ py: 2 }}>
      <Alert icon={<ErrorOutlineIcon />} severity="error">
        {message}
      </Alert>
    </Box>
  );
}
