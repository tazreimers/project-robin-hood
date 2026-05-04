"use client";

import { Alert, Box, CssBaseline, Snackbar, ThemeProvider, useMediaQuery } from "@mui/material";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getScanRun, getScanRuns, startScan } from "../../lib/api";
import { darkTheme, lightTheme } from "../../theme";
import type { ScanRun } from "../../types/api";
import { useLocalStorage } from "../../hooks/useLocalStorage";
import AppSidebar, { collapsedDrawerWidth, expandedDrawerWidth } from "./AppSidebar";
import AppTopBar from "./AppTopBar";

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

type SnackbarState = {
  message: string;
  severity: "success" | "error" | "info";
} | null;

export default function AppShell({ children }: { children: ReactNode }) {
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");
  const [mode, setMode] = useLocalStorage<"light" | "dark">("theme-mode", prefersDark ? "dark" : "light");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [latestScan, setLatestScan] = useState<ScanRun | null>(null);
  const [scanRunning, setScanRunning] = useState(false);
  const [snackbar, setSnackbar] = useState<SnackbarState>(null);

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

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <AppTopBar
          drawerWidth={drawerWidth}
          latestScan={latestScan}
          mode={mode}
          scanRunning={scanRunning}
          onModeChange={setMode}
          onRunScan={() => void runScan()}
        />
        <AppSidebar open={sidebarOpen} width={drawerWidth} onToggle={() => setSidebarOpen((value) => !value)} />
        <Box component="main" sx={{ flexGrow: 1, minWidth: 0, height: "100vh", overflow: "auto", pt: 8 }}>
          <Box sx={{ p: { xs: 2, sm: 3 }, maxWidth: 1680, mx: "auto" }}>{children}</Box>
        </Box>
      </Box>
      <Snackbar open={Boolean(snackbar)} autoHideDuration={3600} onClose={() => setSnackbar(null)} anchorOrigin={{ vertical: "bottom", horizontal: "right" }}>
        {snackbar ? (
          <Alert severity={snackbar.severity} variant="filled" onClose={() => setSnackbar(null)}>
            {snackbar.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </ThemeProvider>
  );
}
