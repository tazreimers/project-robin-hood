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
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  formatMoney,
  formatPercent,
  formatDateTime,
  getApiUsage,
  getDashboardMetrics,
  getHealth,
  getScanRun,
  getScanRuns,
  startScan,
} from "../lib/api";
import type { ApiUsage, DashboardMetrics, HealthResponse, ScanRun } from "../types/api";

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [latestScan, setLatestScan] = useState<ScanRun | null>(null);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [apiUsage, setApiUsage] = useState<ApiUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanRunning, setScanRunning] = useState(false);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [healthResponse, scanRuns, metricsResponse, apiUsageResponse] = await Promise.all([
        getHealth(),
        getScanRuns(),
        getDashboardMetrics(),
        getApiUsage(),
      ]);
      setHealth(healthResponse);
      setLatestScan(scanRuns[0] ?? null);
      setMetrics(metricsResponse);
      setApiUsage(apiUsageResponse);
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
        setSnackbar(run.status === "completed" ? "Scan completed" : `Scan ${run.status}`);
        await loadDashboard();
        return;
      }

      await delay(2000);
    }

    setScanRunning(false);
    setScanError("Scan is still running. Refresh the dashboard in a moment.");
  }, [loadDashboard]);

  const runScan = useCallback(async () => {
    setScanError(null);
    setScanRunning(true);
    setSnackbar("Scan started");

    try {
      const run = await startScan();
      setLatestScan(run);
      if (run.status === "blocked") {
        setScanRunning(false);
        setScanError(run.error_message ?? "Scan blocked by quota guard");
        await loadDashboard();
        return;
      }
      await pollScanRun(run.scan_id);
    } catch (runError) {
      setScanError(runError instanceof Error ? runError.message : "Unable to start scan");
      setScanRunning(false);
    }
  }, [loadDashboard, pollScanRun]);

  useEffect(() => {
    void loadDashboard();
    const refreshDashboard = () => {
      void loadDashboard();
    };
    window.addEventListener("scan-completed", refreshDashboard);

    return () => window.removeEventListener("scan-completed", refreshDashboard);
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

  const estimatedScansRemaining = apiUsage?.estimated_scans_remaining ?? null;
  const quotaIsLow = estimatedScansRemaining !== null && estimatedScansRemaining <= 1;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h5">
          Dashboard
        </Typography>
        <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
          Current API status, latest scan results, and scanner controls.
        </Typography>
      </Box>

      {error ? (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void loadDashboard()}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      ) : null}
      {scanError ? <Alert severity="error">{scanError}</Alert> : null}
      {quotaIsLow ? (
        <Alert severity="warning">
          API quota is low. New scans may be blocked to preserve the configured quota buffer.
        </Alert>
      ) : null}

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

        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                API quota
              </Typography>
              <Grid container spacing={2} sx={{ mt: 0.25 }}>
                <Grid size={{ xs: 6, md: 3 }}>
                  <QuotaMetric label="Remaining" value={apiUsage?.latest_remaining_quota} loading={loading} />
                </Grid>
                <Grid size={{ xs: 6, md: 3 }}>
                  <QuotaMetric label="Used" value={apiUsage?.used_quota} loading={loading} />
                </Grid>
                <Grid size={{ xs: 6, md: 3 }}>
                  <QuotaMetric label="Last cost" value={apiUsage?.last_request_cost} loading={loading} />
                </Grid>
                <Grid size={{ xs: 6, md: 3 }}>
                  <QuotaMetric
                    label="Scans remaining"
                    value={apiUsage?.estimated_scans_remaining}
                    loading={loading}
                    tone={quotaIsLow ? "warning.main" : undefined}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard label="Events processed" value={latestScan?.events_processed ?? 0} loading={loading} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Total opportunities"
            value={metrics?.total_opportunities_found ?? 0}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Last scan time"
            value={formatDateTime(latestScan?.completed_at ?? latestScan?.started_at ?? null)}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Actioned"
            value={metrics?.opportunities_actioned ?? 0}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Expired before action"
            value={metrics?.expired_before_action ?? 0}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Recommended profit"
            value={formatMoney(metrics?.total_recommended_profit ?? 0)}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Actual profit/loss"
            value={formatMoney(metrics?.actual_profit_loss ?? 0)}
            loading={loading}
            tone={Number(metrics?.actual_profit_loss ?? 0) >= 0 ? "success.main" : "error.main"}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Average margin"
            value={metrics?.average_margin ? formatPercent(metrics.average_margin) : "N/A"}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard
            label="Average odds age"
            value={metrics?.average_odds_age ? `${Number(metrics.average_odds_age).toFixed(1)}s` : "N/A"}
            loading={loading}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Best bookmaker pairs
              </Typography>
              <TableContainer sx={{ mt: 1 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Pair</TableCell>
                      <TableCell align="right">Opportunities</TableCell>
                      <TableCell align="right">Profit</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metrics?.best_bookmaker_pairs.length ? (
                      metrics.best_bookmaker_pairs.map((pair) => (
                        <TableRow key={pair.bookmaker_pair.join("-")}>
                          <TableCell>{pair.bookmaker_pair.join(" + ")}</TableCell>
                          <TableCell align="right">{pair.opportunities}</TableCell>
                          <TableCell align="right">{formatMoney(pair.total_recommended_profit)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={3}>
                          <Typography color="text.secondary" sx={{ py: 1 }}>
                            No bookmaker pair data yet.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Recent activity
              </Typography>
              <TableContainer sx={{ mt: 1 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Action</TableCell>
                      <TableCell>Opportunity</TableCell>
                      <TableCell>Notes</TableCell>
                      <TableCell>Time</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metrics?.recent_activity.length ? (
                      metrics.recent_activity.map((activity) => (
                        <TableRow key={activity.id}>
                          <TableCell>
                            <Chip size="small" label={activity.action_type} />
                          </TableCell>
                          <TableCell>#{activity.opportunity_id}</TableCell>
                          <TableCell>{activity.notes ?? ""}</TableCell>
                          <TableCell>{formatDateTime(activity.created_at)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4}>
                          <Typography color="text.secondary" sx={{ py: 1 }}>
                            No recent activity.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={3000}
        onClose={() => setSnackbar(null)}
        message={snackbar ?? ""}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      />
    </Stack>
  );
}

function QuotaMetric({
  label,
  value,
  loading,
  tone,
}: {
  label: string;
  value: number | null | undefined;
  loading: boolean;
  tone?: string;
}) {
  return (
    <Box>
      <Typography color="text.secondary" variant="caption">
        {label}
      </Typography>
      <Typography variant="h5" sx={{ mt: 0.5, fontWeight: 800, color: tone }}>
        {loading ? <CircularProgress size={22} /> : value ?? "N/A"}
      </Typography>
    </Box>
  );
}

function SummaryCard({
  label,
  value,
  loading,
  tone,
}: {
  label: string;
  value: number | string;
  loading: boolean;
  tone?: string;
}) {
  return (
    <Card sx={{ height: "100%", "&:hover": { boxShadow: 4, transform: "translateY(-1px)" } }}>
      <CardContent>
        <Typography color="text.secondary" variant="body2">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: tone }}>
          {loading ? <CircularProgress size={26} /> : value}
        </Typography>
      </CardContent>
    </Card>
  );
}
