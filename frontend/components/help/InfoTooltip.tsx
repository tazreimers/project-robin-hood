"use client";

import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { IconButton, Tooltip } from "@mui/material";

export default function InfoTooltip({ title }: { title: string }) {
  return (
    <Tooltip title={title} arrow>
      <IconButton aria-label={title} size="small" sx={{ ml: 0.5, verticalAlign: "middle" }}>
        <InfoOutlinedIcon fontSize="inherit" />
      </IconButton>
    </Tooltip>
  );
}
