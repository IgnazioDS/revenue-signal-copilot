// Slim API surface for the showcase dashboard.
// Two public, unauthenticated GET endpoints back this dashboard:
//   /api/stats           Tier-A telemetry envelope (TELEMETRY_SCHEMA.md)
//   /api/scoring-latest  the latest daily scoring run (ranked accounts + traces)
// Both read git-committed artifacts; there is no client-facing write surface.

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`Public API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** Tier-A workload metrics for revenue-signal-copilot. See TELEMETRY_SCHEMA.md. */
export interface TierAMetrics {
  accounts_total: number;
  accounts_scored_24h: number;
  signals_detected_24h: number;
  high_priority_accounts: number;
}

/** Tier-A telemetry response — the system processes a real (synthetic, public)
 * scoring workload, so mode is "live". */
export interface PublicStats {
  system: string;
  mode?: "live" | "showcase";
  status: "operational" | "degraded" | "down";
  last_deployed_at: string | null;
  last_active_at?: string | null;
  uptime_pct_30d?: number;
  metrics: Partial<TierAMetrics> & {
    [key: string]: number | string | undefined;
  };
  schema_version: number;
  generated_at: string;
}

export function fetchPublicStats(): Promise<PublicStats> {
  return publicFetch<PublicStats>("/api/stats");
}

// --- /api/scoring-latest -----------------------------------------------------

export interface ScoringTraceEntry {
  signal_id: string;
  kind: string;
  source: string;
  captured_at: string;
  age_days: number;
  base_points: number;
  recency_factor: number;
  points: number;
  reason: string;
}

export type Priority = "high" | "watch" | "low";

export interface RankedAccount {
  rank: number;
  account_id: string;
  name: string;
  industry: string;
  score: number;
  priority: Priority;
  evidence_points: number;
  why: string;
  top_kinds: string[];
  trace: ScoringTraceEntry[];
}

export interface SignalBreakdownRow {
  kind: string;
  label: string;
  count: number;
  share: number;
}

export interface ScoringCalibration {
  metric: string;
  k: number;
  precision: number | null;
  baseline_win_rate: number | null;
  labeled_accounts: number;
  note: string;
}

export interface ScoringPreviousRun {
  run_id: string | null;
  generated_at: string | null;
  delta: {
    high_priority_accounts: number | null;
    top_account_changed: boolean;
    top_account: string | null;
  };
}

/** Latest daily scoring run. The numbers come from a synthetic, public fixture
 * (dataset_kind: "synthetic-public") re-scored each day, not live customer data. */
export interface ScoringLatest {
  system: string;
  mode: "live" | "showcase";
  status: "operational" | "degraded" | "down";
  run_id: string;
  fixture: string;
  dataset_kind: string;
  schema_version: number;
  generated_at: string;
  as_of?: string;
  metrics: TierAMetrics;
  calibration: ScoringCalibration | null;
  ranked_accounts: RankedAccount[];
  top_signals: SignalBreakdownRow[];
  previous_run: ScoringPreviousRun | null;
}

export function fetchScoringLatest(): Promise<ScoringLatest> {
  return publicFetch<ScoringLatest>("/api/scoring-latest");
}

// --- pure display helpers (unit-tested) --------------------------------------

/** Map a priority band to a Badge variant. High-priority is a good lead, so it
 * wears the brand accent, not a danger color. */
export function priorityBadgeVariant(priority: string): "brand" | "warning" | "muted" {
  if (priority === "high") return "brand";
  if (priority === "watch") return "warning";
  return "muted";
}

/** Format a signed delta for display ("+3", "-1", "0"); "—" when unknown. */
export function formatDelta(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value > 0 ? `+${value}` : `${value}`;
}

/** Human label for a lift ratio of precision over baseline ("1.4x baseline"). */
export function liftOverBaseline(
  precision: number | null | undefined,
  baseline: number | null | undefined,
): string | null {
  if (!precision || !baseline || baseline <= 0) return null;
  return `${(precision / baseline).toFixed(1)}x baseline`;
}
