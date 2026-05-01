"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type EventRead = {
  id: number;
  home_team: string;
  away_team: string;
  start_time: string;
};

type ActiveArbitrageOpportunity = {
  id: number;
  event: EventRead;
  market_type: string;
  margin: string;
  guaranteed_profit: string;
  freshness_status: string;
};

type ResourceState<T> = {
  data: T;
  error: string | null;
  loading: boolean;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

function formatDateTime(value: string) {
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

export default function OpportunitiesPage() {
  const [opportunitiesState, setOpportunitiesState] = useState<ResourceState<ActiveArbitrageOpportunity[]>>({
    data: [],
    error: null,
    loading: true,
  });

  const loadOpportunities = useCallback(async () => {
    setOpportunitiesState((current) => ({ ...current, loading: true, error: null }));

    try {
      const opportunities = await fetchJson<ActiveArbitrageOpportunity[]>("/opportunities/active");
      setOpportunitiesState({ data: opportunities, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load opportunities";
      setOpportunitiesState({ data: [], error: message, loading: false });
    }
  }, []);

  useEffect(() => {
    void loadOpportunities();
  }, [loadOpportunities]);

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Project Robin Hood</p>
            <h1>Opportunities</h1>
          </div>
          <Link className="linkButton" href="/">
            Dashboard
          </Link>
        </header>

        <section className="panel" aria-labelledby="opportunities-heading">
          <div className="panelHeader">
            <h2 id="opportunities-heading">Active opportunities</h2>
            <button
              className="refreshButton"
              type="button"
              onClick={loadOpportunities}
              disabled={opportunitiesState.loading}
            >
              Refresh
            </button>
          </div>
          <div className="table">
            {opportunitiesState.error ? <p className="notice error">{opportunitiesState.error}</p> : null}
            {!opportunitiesState.error && opportunitiesState.loading ? (
              <p className="notice">Loading opportunities.</p>
            ) : null}
            {!opportunitiesState.error && !opportunitiesState.loading && opportunitiesState.data.length === 0 ? (
              <p className="notice">No active opportunities detected.</p>
            ) : null}
            {opportunitiesState.data.map((opportunity) => (
              <div className="dataRow opportunityListRow" key={opportunity.id}>
                <div className="primaryCell">
                  <span>
                    {opportunity.event.home_team} vs {opportunity.event.away_team}
                  </span>
                  <span className="mutedText">
                    {opportunity.market_type} - {formatDateTime(opportunity.event.start_time)}
                  </span>
                </div>
                <span>{formatPercent(opportunity.margin)}</span>
                <span>{formatMoney(opportunity.guaranteed_profit)}</span>
                <span>{opportunity.freshness_status}</span>
                <Link className="linkButton" href={`/opportunities/${opportunity.id}`}>
                  Details
                </Link>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
