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

export type ApiUsageLog = {
  id: number;
  provider: string;
  endpoint: string;
  sport_key: string | null;
  regions: string;
  markets: string;
  requests_remaining: number | null;
  requests_used: number | null;
  requests_last: number | null;
  estimated_cost: number;
  captured_at: string;
};

export type ApiUsage = {
  latest_remaining_quota: number | null;
  used_quota: number | null;
  last_request_cost: number | null;
  estimated_scans_remaining: number | null;
  usage_logs: ApiUsageLog[];
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
