export interface PrototypeSignal {
  kind: string;
  label: string;
  source: string;
  capturedAt: string;
  ageDays: number;
  effectivePoints: number;
  summary: string;
  sentiment: "positive" | "negative";
}

export interface PrototypeAccount {
  accountId: string;
  accountName: string;
  score: number;
  status: "high urgency" | "worth active pursuit" | "monitor" | "low priority";
  totalPoints: number;
  positivePoints: number;
  negativePoints: number;
  recommendedAction: string;
  outreachAngle: string;
  brief: string[];
  signals: PrototypeSignal[];
}

export const PROTOTYPE_SIGNAL_SCHEMA = {
  requiredColumns: [
    "account_id",
    "account_name",
    "signal_kind",
    "source",
    "captured_at",
    "strength",
    "summary",
  ],
  supportedSignalKinds: [
    "job_change",
    "hiring_plan",
    "tech_stack_change",
    "website_engagement",
    "rep_note",
    "stakeholder_reply",
    "funding_event",
    "negative_note",
    "stalled_opportunity",
  ],
};

export const PROTOTYPE_COMMANDS = {
  scoreCsv:
    "python -m revenue_signal_copilot.cli score-csv examples/revenue_signals.csv --as-of 2026-05-13",
  briefAccount:
    "python -m revenue_signal_copilot.cli brief-account examples/revenue_signals.csv --account-id acct-003 --as-of 2026-05-13",
  scoreJson:
    "python -m revenue_signal_copilot.cli score-csv examples/revenue_signals.csv --as-of 2026-05-13 --format json",
};

export const PROTOTYPE_ACCOUNTS: PrototypeAccount[] = [
  {
    accountId: "acct-001",
    accountName: "Northstar Health",
    score: 46,
    status: "worth active pursuit",
    totalPoints: 46.1,
    positivePoints: 46.1,
    negativePoints: 0,
    recommendedAction:
      "Route to an AE now with a tailored opener grounded in role change plus hiring momentum.",
    outreachAngle:
      "Lead with revops rebuild pain, forecasting cleanup, and first-quarter operator pressure.",
    brief: [
      "A new VP of Revenue Operations joined recently, which creates a credible change window.",
      "The team is hiring into RevOps and enablement, which signals budget and active process redesign.",
      "An internal rep note ties the motion to a concrete forecasting rebuild, not generic intent.",
    ],
    signals: [
      {
        kind: "job_change",
        label: "Executive job change",
        source: "LinkedIn",
        capturedAt: "2026-05-05",
        ageDays: 8,
        effectivePoints: 19.4,
        summary:
          "New VP of Revenue Operations joined from a scaled healthcare SaaS team.",
        sentiment: "positive",
      },
      {
        kind: "hiring_plan",
        label: "Hiring plan",
        source: "Greenhouse",
        capturedAt: "2026-05-08",
        ageDays: 5,
        effectivePoints: 13.6,
        summary: "Hiring for RevOps analysts and sales enablement.",
        sentiment: "positive",
      },
      {
        kind: "rep_note",
        label: "Rep note",
        source: "Sales note",
        capturedAt: "2026-05-10",
        ageDays: 3,
        effectivePoints: 13.1,
        summary:
          "Rep learned the team is rebuilding forecasting after a CRM cleanup.",
        sentiment: "positive",
      },
    ],
  },
  {
    accountId: "acct-003",
    accountName: "Polar Cloud",
    score: 31,
    status: "monitor",
    totalPoints: 30.6,
    positivePoints: 36.1,
    negativePoints: 5.5,
    recommendedAction:
      "Requalify before pushing outreach; use the active stakeholder thread but validate budget timing first.",
    outreachAngle:
      "Continue the existing conversation with examples for similar GTM teams instead of restarting cold.",
    brief: [
      "The best current signal is direct stakeholder engagement, which makes this account real rather than inferred.",
      "A recent tooling shift suggests the team is in operational motion and may accept workflow change.",
      "Finance previously asked to pause evaluations, so the account is active but not cleanly greenlit.",
    ],
    signals: [
      {
        kind: "stakeholder_reply",
        label: "Stakeholder reply",
        source: "Email",
        capturedAt: "2026-05-12",
        ageDays: 1,
        effectivePoints: 19.0,
        summary:
          "Ops leader replied asking for examples from similar GTM teams.",
        sentiment: "positive",
      },
      {
        kind: "tech_stack_change",
        label: "Tech stack change",
        source: "BuiltWith",
        capturedAt: "2026-05-09",
        ageDays: 4,
        effectivePoints: 17.0,
        summary:
          "Recently adopted a new warehouse and activation tooling.",
        sentiment: "positive",
      },
      {
        kind: "negative_note",
        label: "Negative rep note",
        source: "Sales note",
        capturedAt: "2026-03-20",
        ageDays: 54,
        effectivePoints: -5.5,
        summary: "Finance asked to pause evaluations until next quarter.",
        sentiment: "negative",
      },
    ],
  },
  {
    accountId: "acct-002",
    accountName: "Acme Freight",
    score: 0,
    status: "low priority",
    totalPoints: -4.8,
    positivePoints: 7.5,
    negativePoints: 12.3,
    recommendedAction:
      "Do not spend seller time yet; wait for a fresher signal or a new stakeholder entry point.",
    outreachAngle:
      "Treat this as a requalification case, not a normal outbound sequence.",
    brief: [
      "The website engagement is real but weak relative to the stalled-opportunity drag.",
      "The prior opportunity failed because no internal owner emerged, which makes timing suspect.",
      "This account needs a stronger new signal before it deserves prioritized coverage.",
    ],
    signals: [
      {
        kind: "stalled_opportunity",
        label: "Stalled opportunity",
        source: "CRM",
        capturedAt: "2026-04-01",
        ageDays: 42,
        effectivePoints: -12.3,
        summary:
          "Previous opportunity stalled after no internal owner stepped up.",
        sentiment: "negative",
      },
      {
        kind: "website_engagement",
        label: "Website engagement",
        source: "Website analytics",
        capturedAt: "2026-05-11",
        ageDays: 2,
        effectivePoints: 7.5,
        summary: "Visited pricing and case study pages twice this week.",
        sentiment: "positive",
      },
    ],
  },
];
