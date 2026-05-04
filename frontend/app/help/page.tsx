"use client";

import { Accordion, AccordionDetails, AccordionSummary, Alert, Card, CardContent, Chip, Grid, Stack, Typography } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import HelpCallout from "../../components/help/HelpCallout";
import PageHeader from "../../components/layout/PageHeader";

const sections = [
  {
    title: "What This App Does",
    body: "Project Robin Hood scans permitted odds feeds, detects pricing gaps, and presents manual instructions for review.",
  },
  {
    title: "How Scans Work",
    body: "A scan fetches odds, normalises events and markets, stores fresh snapshots, runs market quality checks, then evaluates arbitrage candidates.",
  },
  {
    title: "What An Arbitrage Opportunity Means",
    body: "An opportunity means the current best prices imply a total probability below 100 percent. It is not a guarantee that the prices will still exist when you inspect them.",
  },
  {
    title: "How To Read An Opportunity",
    body: "Review the event, market, freshness status, margin, recommended stake per leg, and expected return. Every leg must still be available before acting.",
  },
  {
    title: "Why Odds Can Go Stale",
    body: "Bookmakers can move or suspend prices quickly. The app flags stale odds when the latest supporting snapshot is older than the configured freshness window.",
  },
  {
    title: "What API Quota Means",
    body: "Provider APIs charge credits per request. The quota guard estimates scan cost and blocks scans when remaining budget or scan frequency is unsafe.",
  },
  {
    title: "Manual Execution Checklist",
    body: "Open each bookmaker manually, confirm the event, market, outcome, odds, and stake, then record actual odds/stakes in the execution form.",
  },
  {
    title: "Troubleshooting",
    body: "If no data appears, seed demo data, verify the API is healthy, check Docker services, and confirm your API key and quota before live scans.",
  },
  {
    title: "Safety Notes",
    body: "The app does not place bets, log in to bookmaker accounts, solve captchas, bypass KYC/geolocation controls, or bypass responsible gambling controls.",
  },
];

export default function HelpPage() {
  return (
    <Stack spacing={3}>
      <PageHeader title="Help" description="Operational guidance for using the scanner safely and understanding what the UI is showing." />

      <HelpCallout severity="warning">
        This app provides analytics and manual instructions only. You must verify every leg yourself before taking any action outside the app.
      </HelpCallout>

      <Grid container spacing={2}>
        {["Manual only", "Quota-aware", "Freshness checked", "No account control"].map((label) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={label}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Chip label={label} color="primary" />
                <Typography color="text.secondary" variant="body2" sx={{ mt: 1.5 }}>
                  Built to support fast review while keeping execution outside the application.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Help Centre
          </Typography>
          {sections.map((section) => (
            <Accordion key={section.title} disableGutters>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontWeight: 700 }}>{section.title}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography color="text.secondary">{section.body}</Typography>
              </AccordionDetails>
            </Accordion>
          ))}
        </CardContent>
      </Card>

      <Alert severity="info">For developer setup and troubleshooting, see the Markdown docs in the repository `docs/` directory.</Alert>
    </Stack>
  );
}
