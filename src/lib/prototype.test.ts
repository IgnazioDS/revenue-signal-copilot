import { describe, expect, it } from "vitest";
import {
  PROTOTYPE_SIGNAL_SCHEMA,
  PROTOTYPE_COMMANDS,
  PROTOTYPE_ACCOUNTS,
} from "./prototype";

describe("PROTOTYPE_SIGNAL_SCHEMA", () => {
  it("defines all required columns", () => {
    expect(PROTOTYPE_SIGNAL_SCHEMA.requiredColumns).toContain("account_id");
    expect(PROTOTYPE_SIGNAL_SCHEMA.requiredColumns).toContain("signal_kind");
    expect(PROTOTYPE_SIGNAL_SCHEMA.requiredColumns).toContain("source");
    expect(PROTOTYPE_SIGNAL_SCHEMA.requiredColumns.length).toBeGreaterThanOrEqual(
      5,
    );
  });

  it("has non-empty supported signal kinds list", () => {
    expect(
      PROTOTYPE_SIGNAL_SCHEMA.supportedSignalKinds.length,
    ).toBeGreaterThan(0);
    expect(PROTOTYPE_SIGNAL_SCHEMA.supportedSignalKinds).toContain("job_change");
    expect(PROTOTYPE_SIGNAL_SCHEMA.supportedSignalKinds).toContain(
      "hiring_plan",
    );
  });

  it("includes all known signal types", () => {
    const knownKinds = [
      "job_change",
      "hiring_plan",
      "tech_stack_change",
      "website_engagement",
      "rep_note",
      "stakeholder_reply",
      "funding_event",
      "negative_note",
      "stalled_opportunity",
    ];
    for (const kind of knownKinds) {
      expect(PROTOTYPE_SIGNAL_SCHEMA.supportedSignalKinds).toContain(kind);
    }
  });
});

describe("PROTOTYPE_COMMANDS", () => {
  it("has well-formed CLI commands", () => {
    expect(PROTOTYPE_COMMANDS.scoreCsv).toContain("score-csv");
    expect(PROTOTYPE_COMMANDS.scoreCsv).toContain("examples/revenue_signals.csv");
  });

  it("has score, brief, and JSON format commands", () => {
    expect(PROTOTYPE_COMMANDS.scoreCsv).toBeTruthy();
    expect(PROTOTYPE_COMMANDS.briefAccount).toBeTruthy();
    expect(PROTOTYPE_COMMANDS.scoreJson).toBeTruthy();
  });

  it("includes date flags in commands", () => {
    expect(PROTOTYPE_COMMANDS.scoreCsv).toContain("--as-of");
  });
});

describe("PROTOTYPE_ACCOUNTS", () => {
  it("has non-empty accounts array", () => {
    expect(PROTOTYPE_ACCOUNTS.length).toBeGreaterThan(0);
  });

  it("has at least three accounts", () => {
    expect(PROTOTYPE_ACCOUNTS.length).toBeGreaterThanOrEqual(3);
  });

  it("all accounts have required identity fields", () => {
    for (const account of PROTOTYPE_ACCOUNTS) {
      expect(account.accountId).toBeTruthy();
      expect(account.accountName).toBeTruthy();
      expect(typeof account.score).toBe("number");
      expect(account.status).toBeTruthy();
    }
  });

  it("all accounts have signal arrays", () => {
    for (const account of PROTOTYPE_ACCOUNTS) {
      expect(Array.isArray(account.signals)).toBe(true);
      expect(account.signals.length).toBeGreaterThan(0);
    }
  });

  it("all signals have required fields", () => {
    for (const account of PROTOTYPE_ACCOUNTS) {
      for (const signal of account.signals) {
        expect(signal.kind).toBeTruthy();
        expect(signal.source).toBeTruthy();
        expect(signal.capturedAt).toBeTruthy();
        expect(typeof signal.ageDays).toBe("number");
        expect(["positive", "negative"]).toContain(signal.sentiment);
      }
    }
  });

  it("contains valid statuses", () => {
    const validStatuses = [
      "high urgency",
      "worth active pursuit",
      "monitor",
      "low priority",
    ];
    for (const account of PROTOTYPE_ACCOUNTS) {
      expect(validStatuses).toContain(account.status);
    }
  });

  it("has brief field with bullet points", () => {
    for (const account of PROTOTYPE_ACCOUNTS) {
      expect(Array.isArray(account.brief)).toBe(true);
      expect(account.brief.length).toBeGreaterThan(0);
      for (const point of account.brief) {
        expect(point.length).toBeGreaterThan(10);
      }
    }
  });

  it("has recommendation and outreach angle", () => {
    for (const account of PROTOTYPE_ACCOUNTS) {
      expect(account.recommendedAction.length).toBeGreaterThan(10);
      expect(account.outreachAngle.length).toBeGreaterThan(10);
    }
  });

  it("accounts have consistent point calculations", () => {
    for (const account of PROTOTYPE_ACCOUNTS) {
      const sum = account.positivePoints - account.negativePoints;
      expect(Math.abs(sum - account.totalPoints)).toBeLessThan(1);
    }
  });

  it("first account has expected structure", () => {
    const first = PROTOTYPE_ACCOUNTS[0];
    expect(first.accountId).toBe("acct-001");
    expect(first.accountName).toBe("Northstar Health");
    expect(first.score).toBeGreaterThan(0);
  });
});
