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

import { formatDateTime, getScanPriorities } from "../../lib/api";
import type { EventScanPriority } from "../../types/api";

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
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Scan Priorities
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Adaptive polling schedule for upcoming events.
        </Typography>
      </Box>

      {error ? <Alert severity="error">{error}</Alert> : null}

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
                  <Stack sx={{ alignItems: "center", py: 4 }}>
                    <CircularProgress />
                  </Stack>
                </TableCell>
              </TableRow>
            ) : priorities.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary" sx={{ py: 2 }}>
                    No scan priorities have been scheduled.
                  </Typography>
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
                    <Chip
                      size="small"
                      label={priority.priority_level}
                      color={priorityColor(priority.priority_level)}
                    />
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

function priorityColor(priority: EventScanPriority["priority_level"]): "success" | "warning" | "error" | "default" {
  if (priority === "URGENT") {
    return "error";
  }
  if (priority === "HIGH") {
    return "warning";
  }
  if (priority === "NORMAL") {
    return "success";
  }
  return "default";
}
