"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

type ApiState = {
  health: HealthResponse | null;
  error: string | null;
  loading: boolean;
};

type ScanRun = {
  id: number;
  scan_id: number;
  status: string;
  sports_scanned: number;
  events_processed: number;
  markets_processed: number;
  snapshots_saved: number;
  opportunities_found: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

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

type ActiveArbitrageLeg = {
  id: number;
  bookmaker: BookmakerRead;
  outcome_name: string;
  decimal_odds: string;
  stake: string;
  expected_return: string;
};

type ActiveArbitrageOpportunity = {
  id: number;
  event: EventRead;
  market_type: string;
  line: string | null;
  margin: string;
  guaranteed_profit: string;
  guaranteed_return: string;
  detected_at: string;
  freshness_status: string;
  legs: ActiveArbitrageLeg[];
};

type ResourceState<T> = {
  data: T;
  error: string | null;
  loading: boolean;
};

type ScanState = {
  error: string | null;
  run: ScanRun | null;
  submitting: boolean;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not completed";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatMoney(value: string | number) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function formatPercent(value: string) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>({
    health: null,
    error: null,
    loading: true,
  });
  const [latestScanState, setLatestScanState] = useState<ResourceState<ScanRun | null>>({
    data: null,
    error: null,
    loading: true,
  });
  const [opportunitiesState, setOpportunitiesState] = useState<ResourceState<ActiveArbitrageOpportunity[]>>({
    data: [],
    error: null,
    loading: true,
  });
  const [scanState, setScanState] = useState<ScanState>({
    error: null,
    run: null,
    submitting: false,
  });

  const loadHealth = useCallback(async () => {
    setApiState((current) => ({ ...current, loading: true, error: null }));

    try {
      const health = await fetchJson<HealthResponse>("/health");
      setApiState({ health, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to reach API";
      setApiState({ health: null, error: message, loading: false });
    }
  }, []);

  const loadLatestScan = useCallback(async () => {
    setLatestScanState((current) => ({ ...current, loading: true, error: null }));

    try {
      const scanRuns = await fetchJson<ScanRun[]>("/scan-runs");
      setLatestScanState({ data: scanRuns[0] ?? null, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load scan runs";
      setLatestScanState({ data: null, error: message, loading: false });
    }
  }, []);

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

  const refreshDashboard = useCallback(async () => {
    await Promise.all([loadLatestScan(), loadOpportunities()]);
  }, [loadLatestScan, loadOpportunities]);

  const pollScanRun = useCallback(
    async (scanId: number) => {
      for (let attempt = 0; attempt < 60; attempt += 1) {
        const run = await fetchJson<ScanRun>(`/scan-runs/${scanId}`);
        const stillRunning = run.status === "queued" || run.status === "running";
        setScanState({ error: null, run, submitting: stillRunning });

        if (!stillRunning) {
          await refreshDashboard();
          return;
        }

        await delay(2000);
      }

      setScanState((current) => ({
        ...current,
        error: "Scan is still running. Refresh the dashboard in a moment.",
        submitting: false,
      }));
    },
    [refreshDashboard],
  );

  const runScan = useCallback(async () => {
    setScanState({ error: null, run: null, submitting: true });

    try {
      const run = await fetchJson<ScanRun>("/scan", { method: "POST" });
      setScanState({ error: null, run, submitting: true });
      await pollScanRun(run.scan_id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to start scan";
      setScanState({ error: message, run: null, submitting: false });
    }
  }, [pollScanRun]);

  useEffect(() => {
    void loadHealth();
    void refreshDashboard();
  }, [loadHealth, refreshDashboard]);

  const badge = useMemo(() => {
    if (apiState.loading) {
      return { className: "statusBadge", label: "Checking" };
    }

    if (apiState.error) {
      return { className: "statusBadge error", label: "Offline" };
    }

    return { className: "statusBadge ok", label: "Online" };
  }, [apiState.error, apiState.loading]);

  const displayedScan = scanState.run ?? latestScanState.data;

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Project Robin Hood</p>
            <h1>Arbitrage Scanner</h1>
          </div>
          <div className="topbarActions">
            <Link className="linkButton" href="/opportunities">
              Opportunities
            </Link>
            <span className={badge.className}>{badge.label}</span>
          </div>
        </header>

        <div className="summaryGrid">
          <section className="panel" aria-labelledby="api-status-heading">
            <div className="panelHeader">
              <h2 id="api-status-heading">API status</h2>
              <button className="refreshButton" type="button" onClick={loadHealth} disabled={apiState.loading}>
                Refresh
              </button>
            </div>

            <div className="statusBody">
              {apiState.error ? (
                <p className="notice error">{apiState.error}</p>
              ) : apiState.health ? (
                <>
                  <div className="metric">
                    <span className="metricLabel">Status</span>
                    <span className="metricValue">{apiState.health.status}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Service</span>
                    <span className="metricValue">{apiState.health.service}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Environment</span>
                    <span className="metricValue">{apiState.health.environment}</span>
                  </div>
                </>
              ) : (
                <p className="notice">Checking API health.</p>
              )}
            </div>
          </section>

          <section className="panel" aria-labelledby="scan-heading">
            <div className="panelHeader">
              <h2 id="scan-heading">Latest scan</h2>
              <button className="primaryButton" type="button" onClick={runScan} disabled={scanState.submitting}>
                {scanState.submitting ? "Scanning" : "Run scan now"}
              </button>
            </div>

            <div className="statusBody">
              {latestScanState.error ? <p className="notice error">{latestScanState.error}</p> : null}
              {scanState.error ? <p className="notice error">{scanState.error}</p> : null}
              {displayedScan ? (
                <>
                  <div className="metric">
                    <span className="metricLabel">Scan ID</span>
                    <span className="metricValue">#{displayedScan.scan_id}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Status</span>
                    <span className="metricValue">{displayedScan.status}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Sports</span>
                    <span className="metricValue">{displayedScan.sports_scanned}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Events</span>
                    <span className="metricValue">{displayedScan.events_processed}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Markets</span>
                    <span className="metricValue">{displayedScan.markets_processed}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Snapshots</span>
                    <span className="metricValue">{displayedScan.snapshots_saved}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Opportunities</span>
                    <span className="metricValue">{displayedScan.opportunities_found}</span>
                  </div>
                  <div className="metric">
                    <span className="metricLabel">Completed</span>
                    <span className="metricValue">{formatDateTime(displayedScan.completed_at)}</span>
                  </div>
                  {displayedScan.error_message ? <p className="notice error">{displayedScan.error_message}</p> : null}
                </>
              ) : latestScanState.loading ? (
                <p className="notice">Loading scan history.</p>
              ) : (
                <p className="notice">No scans have run yet.</p>
              )}
            </div>
          </section>
        </div>

        <div className="contentGrid">
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
                <div className="dataRow activeOpportunityRow" key={opportunity.id}>
                  <div className="primaryCell">
                    <Link href={`/opportunities/${opportunity.id}`}>
                      {opportunity.event.home_team} vs {opportunity.event.away_team}
                    </Link>
                    <span className="mutedText">
                      {opportunity.market_type} - {formatDateTime(opportunity.event.start_time)}
                    </span>
                  </div>
                  <span>{formatPercent(opportunity.margin)}</span>
                  <span>{formatMoney(opportunity.guaranteed_profit)}</span>
                  <span>{opportunity.freshness_status}</span>
                  <div className="legsCell">
                    {opportunity.legs.map((leg) => (
                      <span className="mutedText" key={leg.id}>
                        {leg.bookmaker.name}: {leg.outcome_name} @ {leg.decimal_odds}, stake{" "}
                        {formatMoney(leg.stake)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
