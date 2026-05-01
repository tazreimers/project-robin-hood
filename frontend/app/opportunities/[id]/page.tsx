"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type EventRead = {
  id: number;
  home_team: string;
  away_team: string;
  start_time: string;
};

type BookmakerRead = {
  id: number;
  name: string;
};

type InstructionLeg = {
  id: number;
  bookmaker: BookmakerRead;
  outcome_name: string;
  decimal_odds: string;
  stake: string;
  expected_return: string;
  source_last_seen_at: string | null;
  odds_age_seconds: number | null;
  instruction: string;
};

type OpportunityInstructions = {
  id: number;
  event: EventRead;
  market: string;
  line: string | null;
  total_stake: string;
  guaranteed_profit: string;
  guaranteed_return: string;
  margin: string;
  legs: InstructionLeg[];
  instructions: string[];
  warning: string;
};

type ResourceState<T> = {
  data: T;
  error: string | null;
  loading: boolean;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatMoney(value: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function formatPercent(value: string) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}

export default function OpportunityDetailPage({ params }: { params: { id: string } }) {
  const [instructionsState, setInstructionsState] = useState<ResourceState<OpportunityInstructions | null>>({
    data: null,
    error: null,
    loading: true,
  });
  const [actionState, setActionState] = useState<{ error: string | null; actioned: boolean; submitting: boolean }>({
    error: null,
    actioned: false,
    submitting: false,
  });

  const loadInstructions = useCallback(async () => {
    setInstructionsState((current) => ({ ...current, loading: true, error: null }));

    try {
      const instructions = await fetchJson<OpportunityInstructions>(`/opportunities/${params.id}/instructions`);
      setInstructionsState({ data: instructions, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load instructions";
      setInstructionsState({ data: null, error: message, loading: false });
    }
  }, [params.id]);

  const markActioned = useCallback(async () => {
    setActionState((current) => ({ ...current, error: null, submitting: true }));

    try {
      await fetchJson(`/opportunities/${params.id}/mark-actioned`, { method: "POST" });
      setActionState({ error: null, actioned: true, submitting: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to mark opportunity as actioned";
      setActionState({ error: message, actioned: false, submitting: false });
    }
  }, [params.id]);

  useEffect(() => {
    void loadInstructions();
  }, [loadInstructions]);

  const instructions = instructionsState.data;

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Manual instructions</p>
            <h1>{instructions ? `${instructions.event.home_team} vs ${instructions.event.away_team}` : "Opportunity"}</h1>
          </div>
          <Link className="linkButton" href="/opportunities">
            Opportunities
          </Link>
        </header>

        {instructionsState.error ? <p className="notice error">{instructionsState.error}</p> : null}
        {instructionsState.loading ? <p className="notice">Loading instructions.</p> : null}

        {instructions ? (
          <div className="contentGrid">
            <section className="panel" aria-labelledby="summary-heading">
              <div className="panelHeader">
                <h2 id="summary-heading">Summary</h2>
                <button
                  className="primaryButton"
                  type="button"
                  onClick={markActioned}
                  disabled={actionState.submitting || actionState.actioned}
                >
                  {actionState.actioned ? "Actioned" : "Mark as actioned"}
                </button>
              </div>
              <div className="statusBody">
                <div className="metric">
                  <span className="metricLabel">Market</span>
                  <span className="metricValue">{instructions.market}</span>
                </div>
                <div className="metric">
                  <span className="metricLabel">Start time</span>
                  <span className="metricValue">{formatDateTime(instructions.event.start_time)}</span>
                </div>
                <div className="metric">
                  <span className="metricLabel">Total stake</span>
                  <span className="metricValue">{formatMoney(instructions.total_stake)}</span>
                </div>
                <div className="metric">
                  <span className="metricLabel">Return</span>
                  <span className="metricValue">{formatMoney(instructions.guaranteed_return)}</span>
                </div>
                <div className="metric">
                  <span className="metricLabel">Profit</span>
                  <span className="metricValue">{formatMoney(instructions.guaranteed_profit)}</span>
                </div>
                <div className="metric">
                  <span className="metricLabel">Margin</span>
                  <span className="metricValue">{formatPercent(instructions.margin)}</span>
                </div>
                {actionState.error ? <p className="notice error">{actionState.error}</p> : null}
                <p className="notice error">{instructions.warning}</p>
              </div>
            </section>

            <section className="panel" aria-labelledby="legs-heading">
              <div className="panelHeader">
                <h2 id="legs-heading">Bookmaker legs</h2>
              </div>
              <div className="table">
                {instructions.legs.map((leg) => (
                  <div className="dataRow instructionLegRow" key={leg.id}>
                    <div className="primaryCell">
                      <span>{leg.bookmaker.name}</span>
                      <span className="mutedText">{leg.instruction}</span>
                    </div>
                    <span>{leg.outcome_name}</span>
                    <span>{leg.decimal_odds}</span>
                    <span>{formatMoney(leg.stake)}</span>
                    <span>{formatMoney(leg.expected_return)}</span>
                    <span className="mutedText">
                      {formatDateTime(leg.source_last_seen_at)}
                      {typeof leg.odds_age_seconds === "number" ? ` (${leg.odds_age_seconds}s old)` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel" aria-labelledby="manual-steps-heading">
              <div className="panelHeader">
                <h2 id="manual-steps-heading">Manual steps</h2>
              </div>
              <div className="statusBody">
                {instructions.instructions.map((instruction) => (
                  <p className="notice" key={instruction}>
                    {instruction}
                  </p>
                ))}
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
