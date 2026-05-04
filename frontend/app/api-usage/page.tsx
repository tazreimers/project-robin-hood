"use client";

import {
  Box,
  Card,
  CardContent,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import EmptyState from "../../components/common/EmptyState";
import ErrorState from "../../components/common/ErrorState";
import LoadingState from "../../components/common/LoadingState";
import PageHeader from "../../components/layout/PageHeader";
import InfoTooltip from "../../components/help/InfoTooltip";
import { formatDateTime } from "../../lib/api";
import { getApiUsage } from "../../lib/api";
import type { ApiUsage } from "../../types/api";

export default function ApiUsagePage() {
  const [usage, setUsage] = useState<ApiUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUsage = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setUsage(await getApiUsage());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load API usage");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUsage();
  }, [loadUsage]);

  if (loading) {
    return <LoadingState message="Loading API usage..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void loadUsage()} />;
  }

  const logs = usage?.usage_logs ?? [];

  return (
    <Stack spacing={3}>
      <PageHeader
        title="API Usage"
        description="Provider quota telemetry captured from odds API responses."
      />

      <Card>
        <CardContent>
          <Typography color="text.secondary" variant="body2">
            API quota
            <InfoTooltip title="Quota values come from provider response headers and are used by the quota guard before scans." />
          </Typography>
          <Grid container spacing={2} sx={{ mt: 0.25 }}>
            <Grid size={{ xs: 6, md: 3 }}>
              <QuotaMetric label="Remaining" value={usage?.latest_remaining_quota} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <QuotaMetric label="Used" value={usage?.used_quota} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <QuotaMetric label="Last cost" value={usage?.last_request_cost} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <QuotaMetric label="Scans remaining" value={usage?.estimated_scans_remaining} />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {logs.length === 0 ? (
        <EmptyState
          title="No API usage recorded yet"
          message="Usage will appear after your first odds request or after seeding local demo data."
        />
      ) : (
        <TableContainer component={Card}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Provider</TableCell>
                <TableCell>Endpoint</TableCell>
                <TableCell>Sport</TableCell>
                <TableCell align="right">Remaining</TableCell>
                <TableCell align="right">Used</TableCell>
                <TableCell align="right">Last</TableCell>
                <TableCell>Captured</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.map((log) => (
                <TableRow hover key={log.id}>
                  <TableCell>{log.provider}</TableCell>
                  <TableCell>{log.endpoint}</TableCell>
                  <TableCell>{log.sport_key ?? "All"}</TableCell>
                  <TableCell align="right">{log.requests_remaining ?? "N/A"}</TableCell>
                  <TableCell align="right">{log.requests_used ?? "N/A"}</TableCell>
                  <TableCell align="right">{log.requests_last ?? log.estimated_cost}</TableCell>
                  <TableCell>{formatDateTime(log.captured_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  );
}

function QuotaMetric({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <Box>
      <Typography color="text.secondary" variant="caption">
        {label}
      </Typography>
      <Typography variant="h5" sx={{ mt: 0.5, fontWeight: 800 }}>
        {value ?? "N/A"}
      </Typography>
    </Box>
  );
}
