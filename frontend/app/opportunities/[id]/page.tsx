"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import {
  formatMoney,
  formatPercent,
  getOpportunityInstructions,
  markOpportunityActioned,
  type OpportunityInstructions,
} from "../../../lib/api";

export default function OpportunityDetailPage({ params }: { params: { id: string } }) {
  const [instructions, setInstructions] = useState<OpportunityInstructions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actioned, setActioned] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadInstructions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setInstructions(await getOpportunityInstructions(params.id));
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
    } catch (markError) {
      setActionError(markError instanceof Error ? markError.message : "Unable to mark opportunity as actioned");
    } finally {
      setSubmitting(false);
    }
  }, [params.id]);

  useEffect(() => {
    void loadInstructions();
  }, [loadInstructions]);

  if (loading) {
    return (
      <Stack sx={{ alignItems: "center", py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  if (error || !instructions) {
    return <Alert severity="error">{error ?? "Opportunity was not found"}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ alignItems: { xs: "stretch", md: "flex-start" }, justifyContent: "space-between" }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            {instructions.event.home_team} vs {instructions.event.away_team}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }} useFlexGap>
            <Chip label={instructions.market} color="primary" />
            <Chip label={`Margin ${formatPercent(instructions.margin)}`} color="success" />
            <Chip label={`Stake ${formatMoney(instructions.total_stake)}`} />
          </Stack>
        </Box>
        <Button
          variant="contained"
          color="secondary"
          startIcon={submitting ? <CircularProgress color="inherit" size={18} /> : <CheckCircleIcon />}
          onClick={markActioned}
          disabled={submitting || actioned}
        >
          {actioned ? "Actioned" : "Mark as Actioned"}
        </Button>
      </Stack>

      <Alert severity="warning">Always verify odds before placing bets</Alert>
      {actionError ? <Alert severity="error">{actionError}</Alert> : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard label="Guaranteed profit" value={formatMoney(instructions.guaranteed_profit)} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard label="Guaranteed return" value={formatMoney(instructions.guaranteed_return)} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <SummaryCard label="Total stake" value={formatMoney(instructions.total_stake)} />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        {instructions.legs.map((leg) => (
          <Grid size={{ xs: 12, md: 6, lg: 4 }} key={leg.id}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Stack spacing={2}>
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Bookmaker
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      {leg.bookmaker.name}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Outcome to bet
                    </Typography>
                    <Typography variant="h6">{leg.outcome_name}</Typography>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Odds
                    </Typography>
                    <Typography variant="h3" color="primary.main" sx={{ fontWeight: 800 }}>
                      {leg.decimal_odds}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={2} sx={{ justifyContent: "space-between" }}>
                    <Box>
                      <Typography color="text.secondary" variant="body2">
                        Stake
                      </Typography>
                      <Typography variant="h6">{formatMoney(leg.stake)}</Typography>
                    </Box>
                    <Box>
                      <Typography color="text.secondary" variant="body2">
                        Expected return
                      </Typography>
                      <Typography variant="h6">{formatMoney(leg.expected_return)}</Typography>
                    </Box>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent>
        <Typography color="text.secondary" variant="body2">
          {label}
        </Typography>
        <Typography variant="h5" sx={{ mt: 1, fontWeight: 700 }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}
