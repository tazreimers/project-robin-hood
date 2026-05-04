import type {
  ActiveArbitrageOpportunity,
  ApiUsage,
  BetRecord,
  BetRecordPayload,
  DashboardMetrics,
  ExecutionLegPatchPayload,
  EventScanPriority,
  HealthResponse,
  MarketQualityCheck,
  OpportunityAction,
  OpportunityExecution,
  OpportunityExecutionCreatePayload,
  OpportunityExecutionPatchPayload,
  OpportunityInstructions,
  ScanRun,
} from "../types/api";
import { API_URL } from "./constants";
import { formatDateTime, formatMoney, formatPercent } from "./formatting";

export type {
  ActiveArbitrageLeg,
  ActiveArbitrageOpportunity,
  ApiUsage,
  ApiUsageLog,
  BetRecord,
  BetRecordPayload,
  BookmakerPairMetric,
  BookmakerRead,
  DashboardMetrics,
  EventRead,
  ExecutionLeg,
  ExecutionLegPatchPayload,
  ExecutionLegStatus,
  EventScanPriority,
  HealthResponse,
  MarketQualityCheck,
  MarketQualityReasons,
  MarketQualityStatus,
  OpportunityAction,
  OpportunityExecution,
  OpportunityExecutionCreatePayload,
  OpportunityExecutionPatchPayload,
  OpportunityExecutionStatus,
  OpportunityInstructionLeg,
  OpportunityInstructions,
  OpportunityValidationReasons,
  RecentActivity,
  ScanRun,
  ScanPriorityEvent,
  ValidationStatus,
} from "../types/api";

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  // API requests are intentionally uncached so scanner state and quota data stay current.
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  // The typed API helpers define the expected response shape at this fetch boundary.
  // eslint-disable-next-line no-type-assertion/no-type-assertion
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

export function getApiUsage() {
  return fetchJson<ApiUsage>("/api-usage");
}

export function getScanPriorities() {
  return fetchJson<EventScanPriority[]>("/scan-priorities");
}

export function getQualityChecks() {
  return fetchJson<MarketQualityCheck[]>("/quality-checks");
}

export function startAdaptiveScan() {
  return fetchJson<{ status: string; task_id: string }>("/jobs/adaptive-scan", { method: "POST" });
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

export function createOpportunityExecution(opportunityId: string, payload: OpportunityExecutionCreatePayload = {}) {
  return fetchJson<OpportunityExecution>(`/opportunities/${opportunityId}/executions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getExecutions() {
  return fetchJson<OpportunityExecution[]>("/executions");
}

export function getExecution(executionId: number) {
  return fetchJson<OpportunityExecution>(`/executions/${executionId}`);
}

export function updateExecution(executionId: number, payload: OpportunityExecutionPatchPayload) {
  return fetchJson<OpportunityExecution>(`/executions/${executionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateExecutionLeg(executionId: number, legId: number, payload: ExecutionLegPatchPayload) {
  return fetchJson<OpportunityExecution>(`/executions/${executionId}/legs/${legId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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

export { formatDateTime, formatMoney, formatPercent };
