"use client";

import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Paper,
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

import { formatDateTime, getScanRuns } from "../../lib/api";
import type { ScanRun } from "../../types/api";

export default function ScanRunsPage() {
  const [scanRuns, setScanRuns] = useState<ScanRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadScanRuns = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setScanRuns(await getScanRuns());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load scan runs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadScanRuns();
  }, [loadScanRuns]);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Scan Runs
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Recent scan history and processing results.
        </Typography>
      </Box>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Scan ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Events processed</TableCell>
              <TableCell>Opportunities found</TableCell>
              <TableCell>Started at</TableCell>
              <TableCell>Completed at</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Stack sx={{ alignItems: "center", py: 4 }}>
                    <CircularProgress />
                  </Stack>
                </TableCell>
              </TableRow>
            ) : scanRuns.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography color="text.secondary" sx={{ py: 2 }}>
                    No scans have run yet.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              scanRuns.map((scanRun) => (
                <TableRow hover key={scanRun.id}>
                  <TableCell>#{scanRun.scan_id}</TableCell>
                  <TableCell>
                    <Chip size="small" label={scanRun.status} color={statusColor(scanRun.status)} />
                  </TableCell>
                  <TableCell>{scanRun.events_processed}</TableCell>
                  <TableCell>{scanRun.opportunities_found}</TableCell>
                  <TableCell>{formatDateTime(scanRun.started_at)}</TableCell>
                  <TableCell>{formatDateTime(scanRun.completed_at)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}

function statusColor(status: string): "success" | "warning" | "error" | "default" {
  if (status === "completed") {
    return "success";
  }

  if (status === "queued" || status === "running") {
    return "warning";
  }

  if (status === "failed") {
    return "error";
  }

  return "default";
}
