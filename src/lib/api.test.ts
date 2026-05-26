import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchPublicStats,
  fetchScoringLatest,
  formatDelta,
  liftOverBaseline,
  priorityBadgeVariant,
} from "./api";

function mockFetch(body: unknown, ok = true, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status,
      statusText: ok ? "OK" : "Server Error",
      json: () => Promise.resolve(body),
    }),
  );
}

describe("fetchPublicStats", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns the parsed Tier-A envelope", async () => {
    mockFetch({
      system: "revenue-signal-copilot",
      mode: "live",
      status: "operational",
      last_deployed_at: null,
      last_active_at: "2026-05-26T06:00:00Z",
      uptime_pct_30d: 100,
      metrics: { accounts_total: 200, high_priority_accounts: 44 },
      schema_version: 1,
      generated_at: "2026-05-26T06:00:00Z",
    });
    const stats = await fetchPublicStats();
    expect(stats.mode).toBe("live");
    expect(stats.metrics.accounts_total).toBe(200);
    expect(stats.uptime_pct_30d).toBe(100);
  });

  it("throws with the status code on a non-ok response", async () => {
    mockFetch({}, false, 503);
    await expect(fetchPublicStats()).rejects.toThrow(/503/);
  });
});

describe("fetchScoringLatest", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns the parsed scoring payload with disclosure fields", async () => {
    mockFetch({
      system: "revenue-signal-copilot",
      mode: "live",
      status: "operational",
      run_id: "rsc-20260526T060000Z",
      fixture: "synthetic-crm-v1",
      dataset_kind: "synthetic-public",
      schema_version: 1,
      generated_at: "2026-05-26T06:00:00Z",
      metrics: {
        accounts_total: 200,
        accounts_scored_24h: 200,
        signals_detected_24h: 7,
        high_priority_accounts: 44,
      },
      calibration: null,
      ranked_accounts: [],
      top_signals: [],
      previous_run: null,
    });
    const scoring = await fetchScoringLatest();
    expect(scoring.dataset_kind).toBe("synthetic-public");
    expect(scoring.fixture).toBe("synthetic-crm-v1");
  });
});

describe("priorityBadgeVariant", () => {
  it("maps each band, with a muted fallback", () => {
    expect(priorityBadgeVariant("high")).toBe("brand");
    expect(priorityBadgeVariant("watch")).toBe("warning");
    expect(priorityBadgeVariant("low")).toBe("muted");
    expect(priorityBadgeVariant("unknown")).toBe("muted");
  });
});

describe("formatDelta", () => {
  it("renders a signed delta", () => {
    expect(formatDelta(3)).toBe("+3");
    expect(formatDelta(-1)).toBe("-1");
    expect(formatDelta(0)).toBe("0");
  });

  it("renders an em-dash for unknown values", () => {
    expect(formatDelta(null)).toBe("—");
    expect(formatDelta(undefined)).toBe("—");
  });
});

describe("liftOverBaseline", () => {
  it("computes the lift ratio", () => {
    expect(liftOverBaseline(0.6, 0.44)).toBe("1.4x baseline");
  });

  it("returns null when either value is missing or baseline is zero", () => {
    expect(liftOverBaseline(null, 0.44)).toBeNull();
    expect(liftOverBaseline(0.6, 0)).toBeNull();
    expect(liftOverBaseline(0.6, null)).toBeNull();
  });
});
