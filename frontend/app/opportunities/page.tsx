"use client";

import VisibilityIcon from "@mui/icons-material/Visibility";
import {
  Alert,
  Box,
  Button,
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
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  type ActiveArbitrageOpportunity,
  formatDateTime,
  formatMoney,
  formatPercent,
  getActiveOpportunities,
} from "../../lib/api";

export default function OpportunitiesPage() {
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<ActiveArbitrageOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setOpportunities(await getActiveOpportunities());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load opportunities");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOpportunities();
    const interval = window.setInterval(() => {
      void loadOpportunities();
    }, 30000);

    return () => window.clearInterval(interval);
  }, [loadOpportunities]);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Opportunities
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Active arbitrage opportunities refresh every 30 seconds.
        </Typography>
      </Box>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Event</TableCell>
              <TableCell>Market</TableCell>
              <TableCell>Margin</TableCell>
              <TableCell>Guaranteed Profit</TableCell>
              <TableCell>Start Time</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <Stack sx={{ alignItems: "center", py: 4 }}>
                    <CircularProgress />
                  </Stack>
                </TableCell>
              </TableRow>
            ) : opportunities.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <Typography color="text.secondary" sx={{ py: 2 }}>
                    No active opportunities detected.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              opportunities.map((opportunity) => (
                <TableRow
                  hover
                  key={opportunity.id}
                  onClick={() => router.push(`/opportunities/${opportunity.id}`)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>
                    {opportunity.event.home_team} vs {opportunity.event.away_team}
                  </TableCell>
                  <TableCell>{opportunity.market_type}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={formatPercent(opportunity.margin)}
                      color={marginColor(Number(opportunity.margin))}
                    />
                  </TableCell>
                  <TableCell>{formatMoney(opportunity.guaranteed_profit)}</TableCell>
                  <TableCell>{formatDateTime(opportunity.event.start_time)}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={opportunity.freshness_status}
                      color={opportunity.freshness_status === "fresh" ? "success" : "warning"}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<VisibilityIcon />}
                      onClick={(event) => {
                        event.stopPropagation();
                        router.push(`/opportunities/${opportunity.id}`);
                      }}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}

function marginColor(margin: number): "success" | "warning" | "error" {
  if (margin > 0.03) {
    return "success";
  }

  if (margin >= 0.01) {
    return "warning";
  }

  return "error";
}
