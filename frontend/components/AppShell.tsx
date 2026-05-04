"use client";

import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import HistoryIcon from "@mui/icons-material/History";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import WbSunnyIcon from "@mui/icons-material/WbSunny";
import {
  Alert,
  AppBar,
  Box,
  Button,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Snackbar,
  Stack,
  Switch,
  ThemeProvider,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { formatDateTime, getScanRun, getScanRuns, startScan } from "../lib/api";
import { darkTheme, lightTheme } from "../theme";
import type { ScanRun } from "../types/api";

const expandedDrawerWidth = 248;
const collapsedDrawerWidth = 76;
const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

const navItems = [
  { label: "Dashboard", href: "/", icon: <DashboardIcon /> },
  { label: "Opportunities", href: "/opportunities", icon: <TrendingUpIcon /> },
  { label: "Scan Runs", href: "/scan-runs", icon: <HistoryIcon /> },
];

type SnackbarState = {
  message: string;
  severity: "success" | "error" | "info";
} | null;

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mode, setMode] = useState<"light" | "dark">("light");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [latestScan, setLatestScan] = useState<ScanRun | null>(null);
  const [scanRunning, setScanRunning] = useState(false);
  const [snackbar, setSnackbar] = useState<SnackbarState>(null);

  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");
  const theme = useMemo(() => (mode === "dark" ? darkTheme : lightTheme), [mode]);
  const drawerWidth = sidebarOpen ? expandedDrawerWidth : collapsedDrawerWidth;

  const loadLatestScan = useCallback(async () => {
    try {
      const runs = await getScanRuns();
      setLatestScan(runs[0] ?? null);
    } catch {
      setLatestScan(null);
    }
  }, []);

  useEffect(() => {
    const storedMode = window.localStorage.getItem("theme-mode");
    if (storedMode === "light" || storedMode === "dark") {
      setMode(storedMode);
      return;
    }
    setMode(prefersDark ? "dark" : "light");
  }, [prefersDark]);

  useEffect(() => {
    window.localStorage.setItem("theme-mode", mode);
  }, [mode]);

  useEffect(() => {
    void loadLatestScan();
  }, [loadLatestScan]);

  const pollScanRun = useCallback(async (scanId: number) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const run = await getScanRun(scanId);
      setLatestScan(run);

      if (run.status !== "queued" && run.status !== "running") {
        setScanRunning(false);
        setSnackbar({
          message: run.status === "completed" ? "Scan completed" : `Scan ${run.status}`,
          severity: run.status === "completed" ? "success" : "info",
        });
        window.dispatchEvent(new Event("scan-completed"));
        return;
      }

      await delay(2000);
    }

    setScanRunning(false);
    setSnackbar({ message: "Scan is still running", severity: "info" });
  }, []);

  const runScan = useCallback(async () => {
    setScanRunning(true);
    setSnackbar({ message: "Scan started", severity: "info" });

    try {
      const run = await startScan();
      setLatestScan(run);
      if (run.status === "blocked") {
        setScanRunning(false);
        setSnackbar({
          message: run.error_message ?? "Scan blocked by quota guard",
          severity: "error",
        });
        window.dispatchEvent(new Event("scan-completed"));
        return;
      }
      await pollScanRun(run.scan_id);
    } catch (error) {
      setScanRunning(false);
      setSnackbar({
        message: error instanceof Error ? error.message : "Unable to start scan",
        severity: "error",
      });
    }
  }, [pollScanRun]);

  const drawer = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar sx={{ minHeight: 64, px: sidebarOpen ? 2 : 1.25 }}>
        <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", minWidth: 0, width: "100%" }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 2,
              bgcolor: "primary.main",
              color: "primary.contrastText",
              display: "grid",
              placeItems: "center",
              fontWeight: 900,
              flex: "0 0 auto",
            }}
          >
            RH
          </Box>
          {sidebarOpen ? (
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.1 }} noWrap>
                Project Robin Hood
              </Typography>
              <Typography color="text.secondary" variant="caption" noWrap>
                Arbitrage terminal
              </Typography>
            </Box>
          ) : null}
        </Stack>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1, py: 1.25 }}>
        {navItems.map((item) => {
          const selected = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Tooltip key={item.href} title={sidebarOpen ? "" : item.label} placement="right">
              <ListItemButton
                component={Link}
                href={item.href}
                selected={selected}
                sx={{
                  borderRadius: 2,
                  mb: 0.75,
                  minHeight: 44,
                  justifyContent: sidebarOpen ? "initial" : "center",
                  px: sidebarOpen ? 1.5 : 1,
                  transition: "background-color 180ms ease, color 180ms ease",
                  "&.Mui-selected": {
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    "& .MuiListItemIcon-root": { color: "primary.contrastText" },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: sidebarOpen ? 40 : 0, color: "inherit" }}>{item.icon}</ListItemIcon>
                {sidebarOpen ? <ListItemText primary={item.label} slotProps={{ primary: { sx: { fontWeight: 700 } } }} /> : null}
              </ListItemButton>
            </Tooltip>
          );
        })}
      </List>
      <Box sx={{ flexGrow: 1 }} />
      <Divider />
      <Box sx={{ p: 1 }}>
        <Tooltip title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"} placement="right">
          <IconButton
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            onClick={() => setSidebarOpen((value) => !value)}
            sx={{ width: "100%", borderRadius: 2 }}
          >
            {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
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
                    onChange={(event) => setMode(event.target.checked ? "dark" : "light")}
                  />
                  <DarkModeIcon fontSize="small" />
                </Stack>
              </Tooltip>
              <Button
                variant="contained"
                color="primary"
                startIcon={scanRunning ? null : <PlayArrowIcon />}
                onClick={runScan}
                disabled={scanRunning}
                sx={{
                  boxShadow: 2,
                  "&:hover": { boxShadow: 5, transform: "translateY(-1px)" },
                }}
              >
                {scanRunning ? "Scanning..." : "Run Scan"}
              </Button>
            </Stack>
          </Toolbar>
        </AppBar>
        <Box component="nav" sx={{ width: drawerWidth, flexShrink: 0, transition: "width 200ms ease" }}>
          <Drawer
            variant="permanent"
            sx={{
              "& .MuiDrawer-paper": {
                boxSizing: "border-box",
                width: drawerWidth,
                overflowX: "hidden",
                transition: "width 200ms ease",
                borderRight: 1,
                borderColor: "divider",
                bgcolor: "background.paper",
              },
            }}
            open
          >
            {drawer}
          </Drawer>
        </Box>
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            minWidth: 0,
            height: "100vh",
            overflow: "auto",
            pt: 8,
          }}
        >
          <Box sx={{ p: { xs: 2, sm: 3 }, maxWidth: 1680, mx: "auto" }}>{children}</Box>
        </Box>
      </Box>
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={3600}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        {snackbar ? (
          <Alert severity={snackbar.severity} variant="filled" onClose={() => setSnackbar(null)}>
            {snackbar.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </ThemeProvider>
  );
}
