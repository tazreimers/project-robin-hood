"use client";

import {
  Card,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import EmptyState from "../../components/common/EmptyState";
import ErrorState from "../../components/common/ErrorState";
import LoadingState from "../../components/common/LoadingState";
import StatusChip from "../../components/common/StatusChip";
import PageHeader from "../../components/layout/PageHeader";
import { formatDateTime, formatMoney, getExecutions } from "../../lib/api";
import type { OpportunityExecution } from "../../types/api";

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<OpportunityExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadExecutions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setExecutions(await getExecutions());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load executions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadExecutions();
  }, [loadExecutions]);

  if (loading) {
    return <LoadingState message="Loading executions..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void loadExecutions()} />;
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Executions"
        description="Manual execution plans and actual odds/stakes entered by the user."
      />

      {executions.length === 0 ? (
        <EmptyState
          title="No executions recorded yet"
          message="Open an opportunity, enter actual odds and stake details, then save the manual execution."
        />
      ) : (
        <TableContainer component={Card}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Opportunity</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Planned stake</TableCell>
                <TableCell align="right">Actual stake</TableCell>
                <TableCell align="right">Expected profit</TableCell>
                <TableCell align="right">Actual profit</TableCell>
                <TableCell>Updated</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {executions.map((execution) => (
                <TableRow hover key={execution.id}>
                  <TableCell>#{execution.id}</TableCell>
                  <TableCell>#{execution.opportunity_id}</TableCell>
                  <TableCell>
                    <StatusChip status={execution.status} />
                  </TableCell>
                  <TableCell align="right">{formatMoney(execution.total_stake_planned)}</TableCell>
                  <TableCell align="right">{formatMoney(execution.total_stake_actual)}</TableCell>
                  <TableCell align="right">{formatMoney(execution.expected_profit)}</TableCell>
                  <TableCell align="right">
                    {execution.actual_profit === null ? "Pending" : formatMoney(execution.actual_profit)}
                  </TableCell>
                  <TableCell>{formatDateTime(execution.updated_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  );
}
