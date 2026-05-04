"use client";

import { Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { formatDateTime, getScanRuns } from "../../lib/api";
import type { ScanRun } from "../../types/api";
import EmptyState from "../../components/common/EmptyState";
import ErrorState from "../../components/common/ErrorState";
import LoadingState from "../../components/common/LoadingState";
import StatusChip from "../../components/common/StatusChip";
import PageHeader from "../../components/layout/PageHeader";

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
      <PageHeader title="Scan Runs" description="Recent scan history and processing results." />

      {error ? <ErrorState message={error} onRetry={() => void loadScanRuns()} /> : null}

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
                  <LoadingState message="Loading scan runs..." />
                </TableCell>
              </TableRow>
            ) : scanRuns.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <EmptyState title="No scan runs yet" message="Start your first scan from the dashboard or the top bar." />
                </TableCell>
              </TableRow>
            ) : (
              scanRuns.map((scanRun) => (
                <TableRow hover key={scanRun.id}>
                  <TableCell>#{scanRun.scan_id}</TableCell>
                  <TableCell>
                    <StatusChip status={scanRun.status} />
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
