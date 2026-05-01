"use client";

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  formatDateTime,
  getHealth,
  getScanRun,
  getScanRuns,
  type HealthResponse,
  type ScanRun,
  startScan,
} from "../lib/api";

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [latestScan, setLatestScan] = useState<ScanRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanRunning, setScanRunning] = useState(false);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [healthResponse, scanRuns] = await Promise.all([getHealth(), getScanRuns()]);
      setHealth(healthResponse);
      setLatestScan(scanRuns[0] ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  const pollScanRun = useCallback(async (scanId: number) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const run = await getScanRun(scanId);
      setLatestScan(run);

      if (run.status !== "queued" && run.status !== "running") {
        setScanRunning(false);
        return;
      }

      await delay(2000);
    }

    setScanRunning(false);
    setScanError("Scan is still running. Refresh the dashboard in a moment.");
  }, []);

  const runScan = useCallback(async () => {
    setScanError(null);
    setScanRunning(true);

    try {
      const run = await startScan();
      setLatestScan(run);
      await pollScanRun(run.scan_id);
    } catch (runError) {
      setScanError(runError instanceof Error ? runError.message : "Unable to start scan");
      setScanRunning(false);
    }
  }, [pollScanRun]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const healthChip = useMemo(() => {
    if (loading && !health) {
      return <Chip label="Checking" color="default" />;
    }

    if (!health || error) {
      return <Chip label="Offline" color="error" />;
    }

    return <Chip label="Online" color="success" />;
  }, [error, health, loading]);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Dashboard
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Current API status, latest scan results, and scanner controls.
        </Typography>
      </Box>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {scanError ? <Alert severity="error">{scanError}</Alert> : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    API health
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 1 }}>
                    {health?.service ?? "Unknown"}
                  </Typography>
                </Box>
                {healthChip}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          <Card>
            <CardContent>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={2}
                sx={{ alignItems: { xs: "stretch", sm: "center" }, justifyContent: "space-between" }}
              >
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Scanner
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 1 }}>
                    {scanRunning ? "Scan running" : latestScan?.status ?? "Ready"}
                  </Typography>
                </Box>
                <Button
                  size="large"
                  variant="contained"
                  startIcon={scanRunning ? <CircularProgress color="inherit" size={18} /> : <PlayArrowIcon />}
                  onClick={runScan}
                  disabled={scanRunning}
                >
                  Run Scan Now
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard label="Events processed" value={latestScan?.events_processed ?? 0} loading={loading} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard label="Opportunities found" value={latestScan?.opportunities_found ?? 0} loading={loading} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Last scan time"
            value={formatDateTime(latestScan?.completed_at ?? latestScan?.started_at ?? null)}
            loading={loading}
          />
        </Grid>
      </Grid>
    </Stack>
  );
}

function SummaryCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: number | string;
  loading: boolean;
}) {
  return (
    <Card>
      <CardContent>
        <Typography color="text.secondary" variant="body2">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ mt: 1, fontWeight: 700 }}>
          {loading ? <CircularProgress size={26} /> : value}
        </Typography>
      </CardContent>
    </Card>
  );
}
