"use client";

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

type FetchOddsResult = {
  status: string;
  reason?: string;
  sport_keys?: string[];
  sports_saved?: number;
  bookmakers_saved?: number;
  events_saved?: number;
  markets_saved?: number;
  outcomes_saved?: number;
  snapshots_saved?: number;
};

type JobStatus = {
  task_id: string;
  state: string;
  ready: boolean;
  successful: boolean;
  result: FetchOddsResult | null;
  error: string | null;
};

type EventRead = {
  id: number;
  home_team: string;
  away_team: string;
  start_time: string;
  normalized_event_key: string;
};

type ArbitrageOpportunityRead = {
  id: number;
  event_id: number;
  market_type: string;
  margin: string;
  guaranteed_profit: string;
  status: string;
  detected_at: string;
};

type ResourceState<T> = {
  data: T;
  error: string | null;
  loading: boolean;
};

type ScanState = {
  error: string | null;
  job: JobStatus | null;
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

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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
  const [eventsState, setEventsState] = useState<ResourceState<EventRead[]>>({
    data: [],
    error: null,
    loading: true,
  });
  const [opportunitiesState, setOpportunitiesState] = useState<ResourceState<ArbitrageOpportunityRead[]>>({
    data: [],
    error: null,
    loading: true,
  });
  const [scanState, setScanState] = useState<ScanState>({
    error: null,
    job: null,
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

  const loadEvents = useCallback(async () => {
    setEventsState((current) => ({ ...current, loading: true, error: null }));

    try {
      const events = await fetchJson<EventRead[]>("/events");
      setEventsState({ data: events, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load events";
      setEventsState({ data: [], error: message, loading: false });
    }
  }, []);

  const loadOpportunities = useCallback(async () => {
    setOpportunitiesState((current) => ({ ...current, loading: true, error: null }));

    try {
      const opportunities = await fetchJson<ArbitrageOpportunityRead[]>("/opportunities");
      setOpportunitiesState({ data: opportunities, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load opportunities";
      setOpportunitiesState({ data: [], error: message, loading: false });
    }
  }, []);

  const loadScannerData = useCallback(async () => {
    await Promise.all([loadEvents(), loadOpportunities()]);
  }, [loadEvents, loadOpportunities]);

  const pollJob = useCallback(
    async (taskId: string) => {
      for (let attempt = 0; attempt < 30; attempt += 1) {
        const job = await fetchJson<JobStatus>(`/jobs/${taskId}`);
        setScanState({ error: null, job, submitting: !job.ready });

        if (job.ready) {
          await loadScannerData();
          return;
        }

        await delay(2000);
      }

      setScanState((current) => ({
        ...current,
        error: "Scan is still running. Refresh the job status in a moment.",
        submitting: false,
      }));
    },
    [loadScannerData],
  );

  const runScan = useCallback(async () => {
    setScanState({ error: null, job: null, submitting: true });

    try {
      const queued = await fetchJson<{ status: string; task_id: string }>("/jobs/fetch-odds", { method: "POST" });
      setScanState({
        error: null,
        job: {
          task_id: queued.task_id,
          state: queued.status.toUpperCase(),
          ready: false,
          successful: false,
          result: null,
          error: null,
        },
        submitting: true,
      });
      await pollJob(queued.task_id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to start scan";
      setScanState({ error: message, job: null, submitting: false });
    }
  }, [pollJob]);

  useEffect(() => {
    void loadHealth();
    void loadScannerData();
  }, [loadHealth, loadScannerData]);

  const badge = useMemo(() => {
    if (apiState.loading) {
      return { className: "statusBadge", label: "Checking" };
    }

    if (apiState.error) {
      return { className: "statusBadge error", label: "Offline" };
    }

    return { className: "statusBadge ok", label: "Online" };
  }, [apiState.error, apiState.loading]);

  const latestScan = scanState.job?.result;

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Project Robin Hood</p>
            <h1>Arbitrage Scanner</h1>
          </div>
          <span className={badge.className}>{badge.label}</span>
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

          <section className="panel" aria-labelledby="queue-heading">
            <div className="panelHeader">
              <h2 id="queue-heading">Scanner queue</h2>
              <button className="primaryButton" type="button" onClick={runScan} disabled={scanState.submitting}>
                {scanState.submitting ? "Scanning" : "Run scan"}
              </button>
            </div>
            <div className="statusBody">
              <div className="metric">
                <span className="metricLabel">Worker</span>
                <span className="metricValue">Celery</span>
              </div>
              <div className="metric">
                <span className="metricLabel">Broker</span>
                <span className="metricValue">Redis</span>
              </div>
              <div className="metric">
                <span className="metricLabel">Scan task</span>
                <span className="metricValue">{scanState.job?.state ?? "Standby"}</span>
              </div>
              {scanState.job ? (
                <div className="metric">
                  <span className="metricLabel">Task ID</span>
                  <span className="metricValue">{scanState.job.task_id}</span>
                </div>
              ) : null}
              {latestScan ? (
                <div className="metric">
                  <span className="metricLabel">Last result</span>
                  <span className="metricValue">
                    {latestScan.status}
                    {typeof latestScan.events_saved === "number" ? `, ${latestScan.events_saved} events` : ""}
                  </span>
                </div>
              ) : null}
              {scanState.error ? <p className="notice error">{scanState.error}</p> : null}
              {scanState.job?.error ? <p className="notice error">{scanState.job.error}</p> : null}
            </div>
          </section>
        </div>

        <div className="contentGrid">
          <section className="panel" aria-labelledby="events-heading">
            <div className="panelHeader">
              <h2 id="events-heading">Upcoming events</h2>
              <button className="refreshButton" type="button" onClick={loadEvents} disabled={eventsState.loading}>
                Refresh
              </button>
            </div>
            <div className="table">
              {eventsState.error ? <p className="notice error">{eventsState.error}</p> : null}
              {!eventsState.error && eventsState.loading ? <p className="notice">Loading events.</p> : null}
              {!eventsState.error && !eventsState.loading && eventsState.data.length === 0 ? (
                <p className="notice">No events loaded.</p>
              ) : null}
              {eventsState.data.map((event) => (
                <div className="dataRow eventRow" key={event.id}>
                  <div className="primaryCell">
                    <span>{event.home_team}</span>
                    <span className="mutedText">vs {event.away_team}</span>
                  </div>
                  <span>{formatDateTime(event.start_time)}</span>
                  <span className="mutedText">#{event.id}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel" aria-labelledby="opportunities-heading">
            <div className="panelHeader">
              <h2 id="opportunities-heading">Opportunities</h2>
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
                <p className="notice">No opportunities detected.</p>
              ) : null}
              {opportunitiesState.data.map((opportunity) => (
                <div className="dataRow opportunityRow" key={opportunity.id}>
                  <div className="primaryCell">
                    <span>Event #{opportunity.event_id}</span>
                    <span className="mutedText">{opportunity.market_type}</span>
                  </div>
                  <span>{formatPercent(opportunity.margin)}</span>
                  <span>{opportunity.status}</span>
                  <span>{formatDateTime(opportunity.detected_at)}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
