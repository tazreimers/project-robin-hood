"use client";

import VisibilityIcon from "@mui/icons-material/Visibility";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
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
  const [includeStale, setIncludeStale] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setOpportunities(await getActiveOpportunities(includeStale));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load opportunities");
    } finally {
      setLoading(false);
    }
  }, [includeStale]);

  useEffect(() => {
    void loadOpportunities();
    const interval = window.setInterval(() => {
      void loadOpportunities();
    }, 30000);

    return () => window.clearInterval(interval);
  }, [loadOpportunities]);

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ alignItems: { xs: "stretch", md: "flex-start" }, justifyContent: "space-between" }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Opportunities
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Active arbitrage opportunities refresh every 30 seconds.
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={includeStale}
              onChange={(event) => setIncludeStale(event.target.checked)}
            />
          }
          label="Include stale"
        />
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Event</TableCell>
              <TableCell>Market</TableCell>
              <TableCell>Margin</TableCell>
              <TableCell>Reliability</TableCell>
              <TableCell>Guaranteed Profit</TableCell>
              <TableCell>Start Time</TableCell>
              <TableCell>Validation</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8}>
                  <Stack sx={{ alignItems: "center", py: 4 }}>
                    <CircularProgress />
                  </Stack>
                </TableCell>
              </TableRow>
            ) : opportunities.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>
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
                  <TableCell>
                    <Chip
                      size="small"
                      label={formatReliabilityScore(opportunity.reliability_score)}
                      color={reliabilityColor(Number(opportunity.reliability_score))}
                    />
                  </TableCell>
                  <TableCell>{formatMoney(opportunity.guaranteed_profit)}</TableCell>
                  <TableCell>{formatDateTime(opportunity.event.start_time)}</TableCell>
                  <TableCell>
                    <Tooltip title={validationTooltip(opportunity)} arrow>
                      <Chip
                        size="small"
                        label={opportunity.validation_status}
                        color={validationColor(opportunity.validation_status)}
                      />
                    </Tooltip>
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

function reliabilityColor(score: number): "success" | "warning" | "error" {
  if (score >= 85) {
    return "success";
  }

  if (score >= 60) {
    return "warning";
  }

  return "error";
}

function validationColor(
  status: ActiveArbitrageOpportunity["validation_status"],
): "success" | "warning" | "error" | "default" {
  if (status === "FRESH") {
    return "success";
  }

  if (status === "RISKY") {
    return "warning";
  }

  if (status === "EXPIRED") {
    return "error";
  }

  return "default";
}

function formatReliabilityScore(value: string | number) {
  return `${Number(value).toFixed(0)}%`;
}

function validationTooltip(opportunity: ActiveArbitrageOpportunity) {
  const reasons = opportunity.validation_reasons.reasons?.length
    ? opportunity.validation_reasons.reasons
    : ["No validation reasons recorded."];

  return (
    <Box sx={{ maxWidth: 360 }}>
      <Stack spacing={0.5}>
        {reasons.map((reason) => (
          <Typography key={reason} variant="body2">
            {reason}
          </Typography>
        ))}
        <Typography color="inherit" variant="caption">
          Odds age: {opportunity.odds_age_seconds ?? "unknown"}s | Starts in:{" "}
          {opportunity.validation_reasons.event_start_minutes ?? "unknown"}m
        </Typography>
      </Stack>
    </Box>
  );
}
