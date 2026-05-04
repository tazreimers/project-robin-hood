import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";
import { Box, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

export default function EmptyState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <Stack spacing={2} sx={{ alignItems: "center", justifyContent: "center", py: 6, textAlign: "center" }}>
      <Box
        sx={{
          width: 52,
          height: 52,
          borderRadius: "50%",
          display: "grid",
          placeItems: "center",
          bgcolor: "action.hover",
          color: "text.secondary",
        }}
      >
        <InboxOutlinedIcon />
      </Box>
      <Box>
        <Typography variant="h6">{title}</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5, maxWidth: 520 }}>
          {message}
        </Typography>
      </Box>
      {action}
    </Stack>
  );
}
