"use client";

import {
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { formatDateTime, getScanPriorities } from "../../lib/api";
import type { EventScanPriority } from "../../types/api";
import EmptyState from "../../components/common/EmptyState";
import ErrorState from "../../components/common/ErrorState";
import LoadingState from "../../components/common/LoadingState";
import StatusChip from "../../components/common/StatusChip";
import PageHeader from "../../components/layout/PageHeader";

export default function ScanPrioritiesPage() {
  const [priorities, setPriorities] = useState<EventScanPriority[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPriorities = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setPriorities(await getScanPriorities());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load scan priorities");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPriorities();
  }, [loadPriorities]);

  return (
    <Stack spacing={3}>
      <PageHeader title="Scan Priorities" description="Adaptive polling schedule for upcoming events." />

      {error ? <ErrorState message={error} onRetry={() => void loadPriorities()} /> : null}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Event</TableCell>
              <TableCell>Start time</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Next scan</TableCell>
              <TableCell>Reason</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <LoadingState message="Loading scan priorities..." />
                </TableCell>
              </TableRow>
            ) : priorities.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <EmptyState
                    title="No scan priorities scheduled"
                    message="Run a scan or seed demo data to create upcoming events with adaptive schedules."
                  />
                </TableCell>
              </TableRow>
            ) : (
              priorities.map((priority) => (
                <TableRow hover key={priority.id}>
                  <TableCell>
                    {priority.event.away_team} at {priority.event.home_team}
                  </TableCell>
                  <TableCell>{formatDateTime(priority.event.start_time)}</TableCell>
                  <TableCell>
                    <StatusChip status={priority.priority_level} />
                  </TableCell>
                  <TableCell>{priority.next_scan_at ? formatDateTime(priority.next_scan_at) : "Not scheduled"}</TableCell>
                  <TableCell>{priority.reason}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}
