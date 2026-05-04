"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import SaveIcon from "@mui/icons-material/Save";
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
  Snackbar,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import ErrorState from "../../../components/common/ErrorState";
import LoadingState from "../../../components/common/LoadingState";
import InfoTooltip from "../../../components/help/InfoTooltip";
import {
  createOpportunityExecution,
  createOpportunityAction,
  formatDateTime,
  formatMoney,
  formatPercent,
  getExecutions,
  getOpportunityInstructions,
  markOpportunityActioned,
  updateExecution,
  updateExecutionLeg,
} from "../../../lib/api";
import type { ExecutionLegStatus, OpportunityExecution, OpportunityInstructions } from "../../../types/api";

const checklistItems = ["Verify odds", "Confirm stake", "Confirm event/time"];
const legStatusOptions: Array<{ label: string; value: ExecutionLegStatus }> = [
  { label: "Placed", value: "PLACED" },
  { label: "Skipped", value: "SKIPPED" },
  { label: "Odds Changed", value: "ODDS_CHANGED" },
];

type LegDraft = {
  actualOdds: string;
  actualStake: string;
  status: ExecutionLegStatus;
  notes: string;
};

export default function OpportunityDetailPage({ params }: { params: { id: string } }) {
  const [instructions, setInstructions] = useState<OpportunityInstructions | null>(null);
  const [execution, setExecution] = useState<OpportunityExecution | null>(null);
  const [legDrafts, setLegDrafts] = useState<Record<number, LegDraft>>({});
  const [executionNotes, setExecutionNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actioned, setActioned] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [executionSaving, setExecutionSaving] = useState(false);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const loadInstructions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [response, executions] = await Promise.all([getOpportunityInstructions(params.id), getExecutions()]);
      const currentExecution = executions.find((item) => String(item.opportunity_id) === params.id) ?? null;
      setInstructions(response);
      setExecution(currentExecution);
      setExecutionNotes(currentExecution?.notes ?? "");
      setLegDrafts(buildLegDrafts(response, currentExecution));
      void createOpportunityAction(params.id, "VIEWED", "Opened execution screen").catch(() => undefined);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load opportunity");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  const updateLegDraft = useCallback((legId: number, field: keyof LegDraft, value: string) => {
    setLegDrafts((current) => ({
      ...current,
      [legId]: {
        ...current[legId],
        [field]: value,
      },
    }));
  }, []);

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

  const saveExecution = useCallback(async () => {
    if (!instructions) {
      return;
    }

    setExecutionSaving(true);
    setActionError(null);

    try {
      let savedExecution =
        execution ??
        (await createOpportunityExecution(params.id, {
          notes: nullableText(executionNotes),
        }));

      savedExecution = await updateExecution(savedExecution.id, {
        notes: nullableText(executionNotes),
      });

      for (const executionLeg of savedExecution.legs) {
        const instructionLeg = instructions.legs.find(
          (leg) => leg.bookmaker.id === executionLeg.bookmaker_id && leg.outcome_name === executionLeg.outcome_name,
        );
        if (!instructionLeg) {
          continue;
        }

        const draft = legDrafts[instructionLeg.id] ?? defaultLegDraft(instructionLeg);
        savedExecution = await updateExecutionLeg(savedExecution.id, executionLeg.id, {
          actual_odds: nullableText(draft.actualOdds),
          actual_stake: nullableText(draft.actualStake),
          status: draft.status,
          notes: nullableText(draft.notes),
        });
      }

      setExecution(savedExecution);
      setLegDrafts(buildLegDrafts(instructions, savedExecution));
      setSnackbar("Execution saved");
    } catch (saveError) {
      setActionError(saveError instanceof Error ? saveError.message : "Unable to save execution");
    } finally {
      setExecutionSaving(false);
    }
  }, [execution, executionNotes, instructions, legDrafts, params.id]);

  const copyInstructions = useCallback(async () => {
    if (!instructions) {
      return;
    }

    try {
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
    } catch {
      setSnackbar("Unable to copy instructions");
    }
  }, [instructions]);

  useEffect(() => {
    void loadInstructions();
  }, [loadInstructions]);

  if (loading) {
    return <LoadingState message="Loading opportunity instructions..." />;
  }

  if (error || !instructions) {
    return <ErrorState message={error ?? "Opportunity was not found"} onRetry={() => void loadInstructions()} />;
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
                  <ExecutionLegFields
                    draft={legDrafts[leg.id] ?? defaultLegDraft(leg)}
                    legId={leg.id}
                    onChange={updateLegDraft}
                  />
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
              <InfoTooltip title="Record what you actually saw and did manually. This does not place bets or control bookmaker accounts." />
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
              <TextField
                fullWidth
                label="Notes"
                multiline
                minRows={2}
                value={executionNotes}
                onChange={(event) => setExecutionNotes(event.target.value)}
                sx={{ mt: 2 }}
              />
              {execution ? (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 2 }} useFlexGap>
                  <Chip label={execution.status} color={executionStatusColor(execution.status)} />
                  <Metric label="Actual stake" value={formatMoney(execution.total_stake_actual)} />
                  <Metric
                    label="Actual profit"
                    value={execution.actual_profit === null ? "Pending" : formatMoney(execution.actual_profit)}
                    success={Number(execution.actual_profit ?? 0) >= 0}
                  />
                </Stack>
              ) : null}
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <Button
                variant="contained"
                color="secondary"
                startIcon={executionSaving ? null : <SaveIcon />}
                onClick={() => void saveExecution()}
                disabled={executionSaving}
              >
                {executionSaving ? "Saving..." : "Save Execution"}
              </Button>
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

function buildLegDrafts(
  instructions: OpportunityInstructions,
  execution: OpportunityExecution | null,
): Record<number, LegDraft> {
  const executionLegs = new Map(
    (execution?.legs ?? []).map((leg) => [`${leg.bookmaker_id}:${leg.outcome_name}`, leg] as const),
  );

  return Object.fromEntries(
    instructions.legs.map((leg) => {
      const executionLeg = executionLegs.get(`${leg.bookmaker.id}:${leg.outcome_name}`);
      return [
        leg.id,
        {
          actualOdds: executionLeg?.actual_odds ?? leg.decimal_odds,
          actualStake: executionLeg?.actual_stake ?? leg.stake,
          status: executionLeg?.status ?? "PLANNED",
          notes: executionLeg?.notes ?? "",
        },
      ];
    }),
  );
}

function defaultLegDraft(leg: OpportunityInstructions["legs"][number]): LegDraft {
  return {
    actualOdds: leg.decimal_odds,
    actualStake: leg.stake,
    status: "PLANNED",
    notes: "",
  };
}

function nullableText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
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

function executionStatusColor(status: string): "success" | "warning" | "error" | "info" | "default" {
  if (status === "ACTIONED" || status === "SETTLED") {
    return "success";
  }
  if (status === "PARTIALLY_ACTIONED" || status === "PLANNED") {
    return "info";
  }
  if (status === "ODDS_CHANGED") {
    return "warning";
  }
  if (status === "SKIPPED") {
    return "default";
  }
  return "default";
}

function ExecutionLegFields({
  draft,
  legId,
  onChange,
}: {
  draft: LegDraft;
  legId: number;
  onChange: (legId: number, field: keyof LegDraft, value: string) => void;
}) {
  return (
    <Stack spacing={1.5}>
      <Divider />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <TextField
          fullWidth
          label="Actual odds"
          size="small"
          value={draft.actualOdds}
          onChange={(event) => onChange(legId, "actualOdds", event.target.value)}
          slotProps={{ input: { inputMode: "decimal" } }}
        />
        <TextField
          fullWidth
          label="Actual stake"
          size="small"
          value={draft.actualStake}
          onChange={(event) => onChange(legId, "actualStake", event.target.value)}
          slotProps={{ input: { inputMode: "decimal" } }}
        />
      </Stack>
      <ToggleButtonGroup
        exclusive
        fullWidth
        size="small"
        value={draft.status === "PLANNED" ? null : draft.status}
        onChange={(_, value: ExecutionLegStatus | null) => {
          onChange(legId, "status", value ?? "PLANNED");
        }}
      >
        {legStatusOptions.map((option) => (
          <ToggleButton key={option.value} value={option.value} sx={{ minHeight: 40 }}>
            {option.label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Stack>
  );
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
