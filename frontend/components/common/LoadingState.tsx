import { CircularProgress, Stack, Typography } from "@mui/material";

export default function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <Stack spacing={2} sx={{ alignItems: "center", justifyContent: "center", py: 8 }}>
      <CircularProgress />
      <Typography color="text.secondary">{message}</Typography>
    </Stack>
  );
}
