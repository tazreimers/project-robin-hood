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

export type BookmakerPairMetric = {
  bookmaker_pair: string[];
  opportunities: number;
  total_recommended_profit: string;
  average_margin: string;
};

export type RecentActivity = {
  id: number;
  opportunity_id: number;
  action_type: string;
  notes: string | null;
  created_at: string;
};

export type DashboardMetrics = {
  total_opportunities_found: number;
  opportunities_actioned: number;
  expired_before_action: number;
  total_recommended_profit: string;
  actual_profit_loss: string;
  average_margin: string | null;
  average_odds_age: string | null;
  best_bookmaker_pairs: BookmakerPairMetric[];
  recent_activity: RecentActivity[];
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

export type ValidationStatus = "FRESH" | "STALE" | "RISKY" | "EXPIRED";

export type OpportunityValidationReasons = {
  odds_age_seconds?: number | null;
  event_start_minutes?: number | null;
  market_consistency_score?: number;
  event_matching_confidence?: number;
  all_legs_available?: boolean;
  recommended_status?: ValidationStatus;
  reasons?: string[];
  leg_checks?: Array<{
    leg_id: number;
    bookmaker_name: string;
    outcome_name: string;
    required_odds: string;
    latest_odds: string | null;
    captured_at: string | null;
    odds_age_seconds: number | null;
    available: boolean;
  }>;
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
  latest_snapshot_at: string | null;
  odds_age_seconds: number | null;
  freshness_status: string;
  reliability_score: string;
  validation_status: ValidationStatus;
  validation_reasons: OpportunityValidationReasons;
  last_validated_at: string | null;
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

export type OpportunityAction = {
  id: number;
  opportunity_id: number;
  action_type: string;
  notes: string | null;
  created_at: string;
};

export type BetRecordPayload = {
  bookmaker_id: number;
  outcome_name: string;
  odds_taken: string;
  recommended_stake: string;
  actual_stake: string;
  result_status?: string;
  payout?: string | null;
  profit_loss?: string | null;
  settled_at?: string | null;
};

export type BetRecord = {
  id: number;
  opportunity_id: number;
  bookmaker_id: number;
  outcome_name: string;
  odds_taken: string;
  recommended_stake: string;
  actual_stake: string;
  result_status: string;
  payout: string | null;
  profit_loss: string | null;
  created_at: string;
  settled_at: string | null;
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

export function getDashboardMetrics() {
  return fetchJson<DashboardMetrics>("/dashboard/metrics");
}

export function getActiveOpportunities(includeStale = false) {
  const query = includeStale ? "?include_stale=true" : "";
  return fetchJson<ActiveArbitrageOpportunity[]>(`/opportunities/active${query}`);
}

export function getOpportunityInstructions(opportunityId: string) {
  return fetchJson<OpportunityInstructions>(`/opportunities/${opportunityId}/instructions`);
}

export function createOpportunityAction(opportunityId: string, actionType: string, notes?: string) {
  return fetchJson<OpportunityAction>(`/opportunities/${opportunityId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_type: actionType, notes: notes ?? null }),
  });
}

export function markOpportunityActioned(opportunityId: string) {
  return fetchJson(`/opportunities/${opportunityId}/mark-actioned`, { method: "POST" });
}

export function createBetRecord(opportunityId: string, payload: BetRecordPayload) {
  return fetchJson<BetRecord>(`/opportunities/${opportunityId}/bet-records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateBetRecord(betRecordId: number, payload: Partial<BetRecordPayload>) {
  return fetchJson<BetRecord>(`/bet-records/${betRecordId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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
