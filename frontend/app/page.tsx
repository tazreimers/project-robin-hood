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

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>({
    health: null,
    error: null,
    loading: true,
  });

  const loadHealth = useCallback(async () => {
    setApiState((current) => ({ ...current, loading: true, error: null }));

    try {
      const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const health = (await response.json()) as HealthResponse;
      setApiState({ health, error: null, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to reach API";
      setApiState({ health: null, error: message, loading: false });
    }
  }, []);

  useEffect(() => {
    void loadHealth();
  }, [loadHealth]);

  const badge = useMemo(() => {
    if (apiState.loading) {
      return { className: "statusBadge", label: "Checking" };
    }

    if (apiState.error) {
      return { className: "statusBadge error", label: "Offline" };
    }

    return { className: "statusBadge ok", label: "Online" };
  }, [apiState.error, apiState.loading]);

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

        <div className="grid">
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
                <span className="metricValue">Standby</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
