"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Divider,
  Grid,
  Skeleton,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import {
  createOpportunityAction,
  formatDateTime,
  formatMoney,
  formatPercent,
  getOpportunityInstructions,
  markOpportunityActioned,
} from "../../../lib/api";
import type { OpportunityInstructions } from "../../../types/api";

const checklistItems = ["Verify odds", "Confirm stake", "Confirm event/time"];

export default function OpportunityDetailPage({ params }: { params: { id: string } }) {
  const [instructions, setInstructions] = useState<OpportunityInstructions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actioned, setActioned] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const loadInstructions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getOpportunityInstructions(params.id);
      setInstructions(response);
      void createOpportunityAction(params.id, "VIEWED", "Opened execution screen").catch(() => undefined);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load opportunity");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  const markActioned = useCallback(async () => {
    setSubmitting(true);
    setActionError(null);

    try {
      await markOpportunityActioned(params.id);
      setActioned(true);
      setSnackbar("Opportunity marked as actioned");
    } catch (markError) {
      setActionError(markError instanceof Error ? markError.message : "Unable to mark opportunity as actioned");
    } finally {
      setSubmitting(false);
    }
  }, [params.id]);

  const copyInstructions = useCallback(async () => {
    if (!instructions) {
      return;
    }

    try {
      const text = [
        `${instructions.event.home_team} vs ${instructions.event.away_team}`,
        `Market: ${instructions.market}`,
        `Margin: ${formatPercent(instructions.margin)}`,
        ...instructions.legs.map(
          (leg) => `${leg.bookmaker.name}: ${leg.outcome_name} @ ${leg.decimal_odds}, stake ${formatMoney(leg.stake)}`,
        ),
      ].join("\n");
      await navigator.clipboard.writeText(text);
      setSnackbar("Bet instructions copied");
    } catch {
      setSnackbar("Unable to copy instructions");
    }
  }, [instructions]);

  useEffect(() => {
    void loadInstructions();
  }, [loadInstructions]);

  if (loading) {
    return (
      <Stack spacing={3}>
        <Skeleton height={180} variant="rounded" />
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Skeleton height={300} variant="rounded" />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Skeleton height={300} variant="rounded" />
          </Grid>
        </Grid>
      </Stack>
    );
  }

  if (error || !instructions) {
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" size="small" onClick={() => void loadInstructions()}>
            Retry
          </Button>
        }
      >
        {error ?? "Opportunity was not found"}
      </Alert>
    );
  }

  const checklistComplete = checklistItems.every((item) => checked[item]);

  return (
    <Stack spacing={3}>
      <Card
        sx={{
          border: 1,
          borderColor: "divider",
          boxShadow: 1,
          "&:hover": { boxShadow: 4 },
        }}
      >
        <CardContent>
          <Stack
            direction={{ xs: "column", lg: "row" }}
            spacing={3}
            sx={{ justifyContent: "space-between", alignItems: { xs: "stretch", lg: "center" } }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h5">
                {instructions.event.home_team} vs {instructions.event.away_team}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }} useFlexGap>
                <Chip label={instructions.market} color="primary" />
                <Chip label={formatDateTime(instructions.event.start_time)} variant="outlined" />
              </Stack>
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={3}>
              <Metric label="Margin" value={formatPercent(instructions.margin)} emphasis />
              <Metric label="Guaranteed profit" value={formatMoney(instructions.guaranteed_profit)} success />
              <Metric label="Total stake" value={formatMoney(instructions.total_stake)} />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {actionError ? <Alert severity="error">{actionError}</Alert> : null}

      <Card sx={{ border: 1, borderColor: "divider" }}>
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            sx={{ alignItems: { xs: "stretch", md: "flex-start" }, justifyContent: "space-between" }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }} useFlexGap>
                <Typography variant="h6">Market quality</Typography>
                {instructions.quality_check ? (
                  <Chip
                    size="small"
                    label={instructions.quality_check.status}
                    color={qualityColor(instructions.quality_check.status)}
                  />
                ) : (
                  <Chip size="small" label="RISKY" color="warning" />
                )}
              </Stack>
              <Stack spacing={0.75} sx={{ mt: 1.5 }}>
                {qualityReasons(instructions.quality_check).map((reason) => (
                  <Typography key={reason} color="text.secondary" variant="body2">
                    {reason}
                  </Typography>
                ))}
              </Stack>
            </Box>
            <Metric
              label="Confidence"
              value={
                instructions.quality_check
                  ? `${(Number(instructions.quality_check.confidence_score) * 100).toFixed(0)}%`
                  : "N/A"
              }
              emphasis
            />
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        {instructions.legs.map((leg) => (
          <Grid size={{ xs: 12, md: 6, lg: 4 }} key={leg.id}>
            <Card
              sx={{
                height: "100%",
                border: 1,
                borderColor: "divider",
                "&:hover": { boxShadow: 5, transform: "translateY(-2px)" },
              }}
            >
              <CardContent>
                <Stack spacing={2.25} sx={{ height: "100%" }}>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                    <Avatar sx={{ bgcolor: "primary.main", color: "primary.contrastText", fontWeight: 800 }}>
                      {leg.bookmaker.name.slice(0, 1)}
                    </Avatar>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="h6" noWrap>
                        {leg.bookmaker.name}
                      </Typography>
                      <Typography color="text.secondary" variant="body2" noWrap>
                        {leg.outcome_name}
                      </Typography>
                    </Box>
                    <Chip
                      size="small"
                      label={leg.freshness_status}
                      color={qualityColor(leg.freshness_status)}
                      sx={{ ml: "auto" }}
                    />
                  </Stack>

                  <Divider />

                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Odds
                    </Typography>
                    <Typography
                      color="primary.main"
                      sx={{ mt: 0.5, fontSize: { xs: 44, md: 52 }, fontFamily: "monospace", fontWeight: 900 }}
                    >
                      {leg.decimal_odds}
                    </Typography>
                  </Box>

                  <Divider />

                  <Stack direction="row" spacing={2} sx={{ justifyContent: "space-between" }}>
                    <Box>
                      <Typography color="text.secondary" variant="body2">
                        Stake
                      </Typography>
                      <Typography sx={{ fontFamily: "monospace", fontWeight: 800 }}>{formatMoney(leg.stake)}</Typography>
                    </Box>
                    <Box sx={{ textAlign: "right" }}>
                      <Typography color="text.secondary" variant="body2">
                        Return
                      </Typography>
                      <Typography sx={{ fontFamily: "monospace", fontWeight: 800 }}>
                        {formatMoney(leg.expected_return)}
                      </Typography>
                    </Box>
                  </Stack>
                  <Typography color="text.secondary" variant="body2">
                    Freshness: {leg.odds_age_seconds === null ? "unknown" : `${leg.odds_age_seconds}s old`}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Card sx={{ border: 1, borderColor: "divider" }}>
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            sx={{ alignItems: { xs: "stretch", md: "center" }, justifyContent: "space-between" }}
          >
            <Box>
              <Typography variant="h6">Execution checklist</Typography>
              <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
                Complete each manual check before marking the opportunity as actioned.
              </Typography>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 1.5 }} useFlexGap>
                {checklistItems.map((item) => (
                  <Stack key={item} direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
                    <Checkbox
                      checked={Boolean(checked[item])}
                      slotProps={{ input: { "aria-label": item } }}
                      onChange={(event) => setChecked((value) => ({ ...value, [item]: event.target.checked }))}
                    />
                    <Typography variant="body2">{item}</Typography>
                  </Stack>
                ))}
              </Stack>
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <Button variant="outlined" startIcon={<ContentCopyIcon />} onClick={() => void copyInstructions()}>
                Copy Instructions
              </Button>
              <Button
                variant="contained"
                color="primary"
                size="large"
                startIcon={submitting ? null : <CheckCircleIcon />}
                onClick={markActioned}
                disabled={submitting || actioned || !checklistComplete}
                sx={{ boxShadow: 2, "&:hover": { boxShadow: 5, transform: "translateY(-1px)" } }}
              >
                {actioned ? "Actioned" : submitting ? "Submitting..." : "Mark as Actioned"}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

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

function qualityReasons(qualityCheck: OpportunityInstructions["quality_check"]) {
  if (!qualityCheck) {
    return ["No quality check was recorded for this opportunity."];
  }

  const failures = qualityCheck.reasons.failures ?? [];
  const warnings = qualityCheck.reasons.warnings ?? [];
  const checks = qualityCheck.reasons.checks ?? [];
  const reasons = [...failures, ...warnings, ...checks].filter(Boolean);
  return reasons.length ? reasons : ["No quality reasons were recorded."];
}

function qualityColor(status: string): "success" | "warning" | "error" | "default" {
  if (status === "VERIFIED") {
    return "success";
  }
  if (status === "RISKY" || status === "STALE") {
    return "warning";
  }
  if (status === "REJECTED") {
    return "error";
  }
  return "default";
}

function Metric({
  label,
  value,
  emphasis = false,
  success = false,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
  success?: boolean;
}) {
  return (
    <Box sx={{ minWidth: 140 }}>
      <Typography color="text.secondary" variant="body2">
        {label}
      </Typography>
      <Typography
        color={success ? "success.main" : "text.primary"}
        sx={{
          mt: 0.5,
          fontFamily: "monospace",
          fontSize: emphasis ? 34 : 26,
          fontWeight: 900,
          lineHeight: 1.05,
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}
