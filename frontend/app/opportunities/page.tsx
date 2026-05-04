"use client";

import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Box, Button, Chip, FormControlLabel, LinearProgress, Paper, Snackbar, Stack, Switch, Tooltip, Typography } from "@mui/material";
import { DataGrid, type GridColDef, type GridRenderCellParams, type GridRowClassNameParams, type GridRowParams } from "@mui/x-data-grid";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { formatDateTime, formatMoney, formatPercent, getActiveOpportunities, getOpportunityInstructions } from "../../lib/api";
import type { ActiveArbitrageOpportunity } from "../../types/api";
import EmptyState from "../../components/common/EmptyState";
import ErrorState from "../../components/common/ErrorState";
import LoadingState from "../../components/common/LoadingState";
import InfoTooltip from "../../components/help/InfoTooltip";

const refreshSeconds = 30;

export default function OpportunitiesPage() {
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<ActiveArbitrageOpportunity[]>([]);
  const [includeStale, setIncludeStale] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(refreshSeconds);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const [updatedIds, setUpdatedIds] = useState<Set<number>>(new Set());
  const previousIds = useRef<Set<number>>(new Set());

  const loadOpportunities = useCallback(
    async (showLoader = false) => {
      if (showLoader) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);

      try {
        const data = await getActiveOpportunities(includeStale);
        const nextIds = new Set(data.map((opportunity) => opportunity.id));
        const newIds = data.map((opportunity) => opportunity.id).filter((id) => previousIds.current.size > 0 && !previousIds.current.has(id));
        previousIds.current = nextIds;
        setOpportunities(data);
        setCountdown(refreshSeconds);

        if (newIds.length > 0) {
          setUpdatedIds(new Set(newIds));
          window.setTimeout(() => setUpdatedIds(new Set()), 2200);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load opportunities");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [includeStale]
  );

  useEffect(() => {
    previousIds.current = new Set();
    void loadOpportunities(true);
  }, [loadOpportunities]);

  useEffect(() => {
    if (!autoRefresh) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setCountdown((value) => {
        if (value <= 1) {
          void loadOpportunities(false);
          return refreshSeconds;
        }
        return value - 1;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [autoRefresh, loadOpportunities]);

  const copyInstructions = useCallback(async (opportunityId: number) => {
    try {
      const instructions = await getOpportunityInstructions(String(opportunityId));
      const text = [
        `Event: ${instructions.event.home_team} vs ${instructions.event.away_team}`,
        `Market: ${instructions.market}`,
        `Margin: ${formatPercent(instructions.margin)}`,
        "",
        ...instructions.legs.flatMap((leg, index) => [
          `Leg ${index + 1}`,
          `Bookmaker: ${leg.bookmaker.name}`,
          `Outcome: ${leg.outcome_name}`,
          `Odds: ${leg.decimal_odds}`,
          `Stake: ${formatMoney(leg.stake)}`,
          `Expected return: ${formatMoney(leg.expected_return)}`,
          "",
        ]),
      ].join("\n");
      await navigator.clipboard.writeText(text);
      setSnackbar("Bet instructions copied");
    } catch (copyError) {
      setSnackbar(copyError instanceof Error ? copyError.message : "Unable to copy instructions");
    }
  }, []);

  const columns = useMemo<GridColDef<ActiveArbitrageOpportunity>[]>(
    () => [
      {
        field: "eventName",
        headerName: "Event",
        minWidth: 240,
        flex: 1.4,
        valueGetter: (_, row) => `${row.event.home_team} vs ${row.event.away_team}`,
        renderCell: (params) => (
          <Stack spacing={0.25} sx={{ minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
              {params.row.event.home_team} vs {params.row.event.away_team}
            </Typography>
            <Typography color="text.secondary" variant="caption" noWrap>
              {formatDateTime(params.row.event.start_time)}
            </Typography>
          </Stack>
        ),
      },
      {
        field: "market_type",
        headerName: "Market",
        width: 120,
        renderCell: (params: GridRenderCellParams<ActiveArbitrageOpportunity, string>) => (
          <Chip size="small" label={params.row.market_type} variant="outlined" />
        ),
      },
      {
        field: "margin",
        renderHeader: () => (
          <Stack direction="row" sx={{ alignItems: "center" }}>
            Margin
            <InfoTooltip title="Margin is the gap between 100% and the best-outcome implied probability total." />
          </Stack>
        ),
        width: 120,
        type: "number",
        valueGetter: (value) => Number(value),
        renderCell: (params: GridRenderCellParams<ActiveArbitrageOpportunity, number>) => (
          <Chip size="small" label={formatPercent(String(params.value ?? 0))} color={marginColor(Number(params.value ?? 0))} />
        ),
      },
      {
        field: "reliability_score",
        headerName: "Reliability",
        width: 130,
        type: "number",
        valueGetter: (value) => Number(value),
        renderCell: (params: GridRenderCellParams<ActiveArbitrageOpportunity, number>) => (
          <Typography variant="body2" sx={{ fontFamily: "monospace", fontWeight: 800 }}>
            {Number(params.value ?? 0).toFixed(0)}%
          </Typography>
        ),
      },
      {
        field: "guaranteed_profit",
        renderHeader: () => (
          <Stack direction="row" sx={{ alignItems: "center" }}>
            Profit
            <InfoTooltip title="Guaranteed profit assumes every listed leg is placed at the quoted odds or better." />
          </Stack>
        ),
        width: 140,
        type: "number",
        valueGetter: (value) => Number(value),
        renderCell: (params: GridRenderCellParams<ActiveArbitrageOpportunity, number>) => (
          <Typography color="success.main" variant="body2" sx={{ fontFamily: "monospace", fontWeight: 800 }}>
            {formatMoney(Number(params.value ?? 0))}
          </Typography>
        ),
      },
      {
        field: "validation_status",
        renderHeader: () => (
          <Stack direction="row" sx={{ alignItems: "center" }}>
            Freshness
            <InfoTooltip title="Fresh, risky, and stale statuses are based on latest odds age and validation checks." />
          </Stack>
        ),
        width: 140,
        renderCell: (params) => (
          <Tooltip title={validationTooltip(params.row)} arrow>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <Box
                sx={{
                  width: 9,
                  height: 9,
                  borderRadius: "50%",
                  bgcolor: freshnessColor(params.row.validation_status),
                }}
              />
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {params.row.validation_status}
              </Typography>
            </Stack>
          </Tooltip>
        ),
      },
      {
        field: "actions",
        headerName: "Actions",
        width: 220,
        sortable: false,
        filterable: false,
        renderCell: (params) => (
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<VisibilityIcon />}
              onClick={(event) => {
                event.stopPropagation();
                router.push(`/opportunities/${params.row.id}`);
              }}
            >
              View
            </Button>
            <Button
              size="small"
              variant="text"
              startIcon={<ContentCopyIcon />}
              onClick={(event) => {
                event.stopPropagation();
                void copyInstructions(params.row.id);
              }}
            >
              Copy
            </Button>
          </Stack>
        ),
      },
    ],
    [copyInstructions, router]
  );

  if (loading && opportunities.length === 0) {
    return (
      <Stack spacing={3}>
        <PageHeader
          autoRefresh={autoRefresh}
          countdown={countdown}
          includeStale={includeStale}
          onAutoRefreshChange={setAutoRefresh}
          onIncludeStaleChange={setIncludeStale}
        />
        <Paper sx={{ p: 2 }}>
          <LoadingState message="Loading opportunities..." />
        </Paper>
      </Stack>
    );
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        autoRefresh={autoRefresh}
        countdown={countdown}
        includeStale={includeStale}
        onAutoRefreshChange={setAutoRefresh}
        onIncludeStaleChange={setIncludeStale}
      />

      {error ? <ErrorState message={error} onRetry={() => void loadOpportunities(true)} /> : null}

      <Paper sx={{ overflow: "hidden", border: 1, borderColor: "divider" }}>
        {refreshing ? <LinearProgress /> : null}
        <DataGrid
          rows={opportunities}
          columns={columns}
          autoHeight
          disableRowSelectionOnClick
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
            sorting: { sortModel: [{ field: "margin", sort: "desc" }] },
          }}
          onRowClick={(params: GridRowParams<ActiveArbitrageOpportunity>) => router.push(`/opportunities/${params.row.id}`)}
          getRowClassName={(params: GridRowClassNameParams<ActiveArbitrageOpportunity>) => (updatedIds.has(Number(params.id)) ? "updated-row" : "")}
          slots={{
            noRowsOverlay: () => (
              <EmptyState title="No opportunities found yet" message="Run a scan to check the latest odds, or seed demo data for a local walkthrough." />
            ),
          }}
          localeText={{ noRowsLabel: "No arbitrage opportunities found" }}
          sx={{
            border: 0,
            "& .MuiDataGrid-row": {
              cursor: "pointer",
              transition: "background-color 180ms ease",
            },
            "& .MuiDataGrid-row:hover": {
              bgcolor: "action.hover",
            },
            "& .updated-row": {
              animation: "rowFlash 2.2s ease",
            },
            "@keyframes rowFlash": {
              "0%": { backgroundColor: "rgba(76, 175, 80, 0.28)" },
              "100%": { backgroundColor: "transparent" },
            },
          }}
        />
      </Paper>

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

function PageHeader({
  autoRefresh,
  countdown,
  includeStale,
  onAutoRefreshChange,
  onIncludeStaleChange,
}: {
  autoRefresh: boolean;
  countdown: number;
  includeStale: boolean;
  onAutoRefreshChange: (value: boolean) => void;
  onIncludeStaleChange: (value: boolean) => void;
}) {
  return (
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: { xs: "stretch", md: "flex-start" }, justifyContent: "space-between" }}>
      <Box>
        <Typography variant="h5">Opportunities</Typography>
        <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
          Active arbitrage board for manual review and execution.
        </Typography>
      </Box>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: { sm: "center" } }}>
        <Chip size="small" color={autoRefresh ? "primary" : "default"} label={`Refresh in ${countdown}s`} />
        <FormControlLabel control={<Switch checked={includeStale} onChange={(event) => onIncludeStaleChange(event.target.checked)} />} label="Include stale" />
        <FormControlLabel
          control={<Switch checked={autoRefresh} onChange={(event) => onAutoRefreshChange(event.target.checked)} />}
          label="Auto-refresh (30s)"
        />
      </Stack>
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

function freshnessColor(status: ActiveArbitrageOpportunity["validation_status"]) {
  if (status === "FRESH") {
    return "success.main";
  }
  if (status === "RISKY") {
    return "warning.main";
  }
  return "text.disabled";
}

function validationTooltip(opportunity: ActiveArbitrageOpportunity) {
  const reasons = opportunity.validation_reasons.reasons?.length ? opportunity.validation_reasons.reasons : ["No validation reasons recorded."];

  return (
    <Box sx={{ maxWidth: 360 }}>
      <Stack spacing={0.5}>
        {reasons.map((reason) => (
          <Typography key={reason} variant="body2">
            {reason}
          </Typography>
        ))}
        <Typography color="inherit" variant="caption">
          Odds age: {opportunity.odds_age_seconds ?? "unknown"}s | Starts in: {opportunity.validation_reasons.event_start_minutes ?? "unknown"}m
        </Typography>
      </Stack>
    </Box>
  );
}
