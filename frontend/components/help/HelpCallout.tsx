import { Alert, type AlertColor } from "@mui/material";
import type { ReactNode } from "react";

export default function HelpCallout({
  children,
  severity = "info",
}: {
  children: ReactNode;
  severity?: AlertColor;
}) {
  return (
    <Alert severity={severity} sx={{ border: 1, borderColor: "divider" }}>
      {children}
    </Alert>
  );
}
