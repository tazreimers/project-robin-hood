import { Box, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

export default function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: { xs: "stretch", md: "flex-start" }, justifyContent: "space-between" }}>
      <Box>
        <Typography variant="h5">{title}</Typography>
        {description ? (
          <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
            {description}
          </Typography>
        ) : null}
      </Box>
      {actions}
    </Stack>
  );
}
