"use client";

import DarkModeIcon from "@mui/icons-material/DarkMode";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import WbSunnyIcon from "@mui/icons-material/WbSunny";
import { AppBar, Box, Button, LinearProgress, Stack, Switch, Toolbar, Tooltip, Typography } from "@mui/material";

import { formatDateTime } from "../../lib/api";
import type { ScanRun } from "../../types/api";
import InfoTooltip from "../help/InfoTooltip";

export default function AppTopBar({
  drawerWidth,
  latestScan,
  mode,
  scanRunning,
  onModeChange,
  onRunScan,
}: {
  drawerWidth: number;
  latestScan: ScanRun | null;
  mode: "light" | "dark";
  scanRunning: boolean;
  onModeChange: (mode: "light" | "dark") => void;
  onRunScan: () => void;
}) {
  return (
    <AppBar
      position="fixed"
      color="inherit"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        ml: `${drawerWidth}px`,
        width: `calc(100% - ${drawerWidth}px)`,
        transition: "margin-left 200ms ease, width 200ms ease",
        backdropFilter: "blur(10px)",
      }}
    >
      {scanRunning ? <LinearProgress color="primary" /> : null}
      <Toolbar sx={{ gap: 2, minHeight: 64 }}>
        <Box sx={{ minWidth: 0, flexGrow: 1 }}>
          <Typography variant="h6" noWrap sx={{ fontWeight: 800 }}>
            Arbitrage Scanner
          </Typography>
          <Typography color="text.secondary" variant="body2" noWrap>
            Last scan: {formatDateTime(latestScan?.completed_at ?? latestScan?.started_at ?? null)}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
          <Tooltip title={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
              <WbSunnyIcon fontSize="small" />
              <Switch
                checked={mode === "dark"}
                slotProps={{ input: { "aria-label": "Toggle dark mode" } }}
                onChange={(event) => onModeChange(event.target.checked ? "dark" : "light")}
              />
              <DarkModeIcon fontSize="small" />
            </Stack>
          </Tooltip>
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <Button
              variant="contained"
              color="primary"
              startIcon={scanRunning ? null : <PlayArrowIcon />}
              onClick={onRunScan}
              disabled={scanRunning}
              sx={{ boxShadow: 2, "&:hover": { boxShadow: 5, transform: "translateY(-1px)" } }}
            >
              {scanRunning ? "Scanning..." : "Run Scan"}
            </Button>
            <InfoTooltip title="Runs the manual scan workflow. The quota guard may block the scan if usage is too high." />
          </Box>
        </Stack>
      </Toolbar>
    </AppBar>
  );
}
