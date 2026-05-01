export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

export type ScanRun = {
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

export type EventRead = {
  id: number;
  home_team: string;
  away_team: string;
  start_time: string;
};

export type BookmakerRead = {
  id: number;
  name: string;
};

export type ActiveArbitrageLeg = {
  id: number;
  bookmaker: BookmakerRead;
  outcome_name: string;
  decimal_odds: string;
  stake: string;
  expected_return: string;
};

export type ActiveArbitrageOpportunity = {
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

export type OpportunityInstructionLeg = {
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

export type OpportunityInstructions = {
  id: number;
  event: EventRead;
  market: string;
  line: string | null;
  total_stake: string;
  guaranteed_profit: string;
  guaranteed_return: string;
  margin: string;
  legs: OpportunityInstructionLeg[];
  instructions: string[];
  warning: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getHealth() {
  return fetchJson<HealthResponse>("/health");
}

export function startScan() {
  return fetchJson<ScanRun>("/scan", { method: "POST" });
}

export function getScanRuns() {
  return fetchJson<ScanRun[]>("/scan-runs");
}

export function getScanRun(scanId: number) {
  return fetchJson<ScanRun>(`/scan-runs/${scanId}`);
}

export function getActiveOpportunities() {
  return fetchJson<ActiveArbitrageOpportunity[]>("/opportunities/active");
}

export function getOpportunityInstructions(opportunityId: string) {
  return fetchJson<OpportunityInstructions>(`/opportunities/${opportunityId}/instructions`);
}

export function markOpportunityActioned(opportunityId: string) {
  return fetchJson(`/opportunities/${opportunityId}/mark-actioned`, { method: "POST" });
}

export function formatDateTime(value: string | null) {
  if (!value) {
    return "Not completed";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatMoney(value: string | number) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function formatPercent(value: string) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}
