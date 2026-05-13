# Revenue Signal Copilot

> Lead intelligence with explainable scoring. Every score traces to a named signal a sales rep can defend in a pipeline review — not a number that is suspiciously precise or suspiciously round.

[**Live dashboard →**](https://revenue-signal-copilot.eleventh.dev) · Stage: Ready to build · Track: AI/ML · Category: Business Tool

---

## Status: showcase-state plus local MVP

**The public dashboard is still in showcase-state, but the Python layer is no longer just a scaffold.** This repository now ships a local MVP slice of the copilot: a typed signal taxonomy, CSV ingestion, recency-decayed scoring, an explainable score trace, and a deterministic account brief built from that trace. CRM integrations, a persistent signal ledger, and a production scoring service are still not in the repo. See [What ships right now](#what-ships-right-now) for the audit.

For an example of what one of these projects looks like once graduated to production, see [NexusRAG](https://github.com/IgnazioDS/NexusRAG) — same operator, same engineering bar, fully shipped.

---

## What this project is

Lead-scoring tools usually treat scoring as a CRM-field-update job: take firmographics, run a model, write a number back. The result is a number that is either suspiciously precise or suspiciously round, and that the sales rep ignores either way — because the rep cannot defend the number in a meeting where they have to justify a 90-minute call slot.

Revenue Signal Copilot inverts the contract. The bottleneck is not the score; it is the signal-to-noise ratio of the inputs and the defensibility of the output. The copilot scores accounts using typed signals (job-change events, hiring posts, infrastructure changes, internal-rep notes), each with explicit recency decay, and emits a trace the rep can read aloud in a pipeline review.

## Architectural thesis

- **Signal taxonomy as first-class data.** Typed signals, not free-text notes. A signal has a kind, a source, a captured-at, and a decay function — never a generic "intent score" that aggregates everything into noise.
- **Scoring as traceable diagnostic.** Every score must explain itself in named-signal terms. A rep reading the trace sees: "this account scored 84 because (1) job-change event 6 days ago at VP+ level, (2) infrastructure-shift signal 12 days ago, (3) prior-rep note from last quarter — minus stale firmographics."
- **Refusal of black-box ML scoring.** A score the rep cannot defend is a score the rep ignores. The model is auditable end-to-end or it is not in the pipeline.
- **Recency decay matters more than signal-source quality.** An 18-month-old signal weighted equal to a 7-day-old one is the most common scoring failure. Time-weighted signals beat un-weighted high-quality ones in practice.

## Failure modes this addresses

| Failure mode | What surfaces in production |
|---|---|
| Score-as-black-box | Rep cannot defend the score in a pipeline review, so the rep ignores it and works leads by gut. |
| Stale-signal contamination | Signals from 18 months ago weighted equal to signals from last week. The score reflects history, not opportunity. |
| Internal-note loss | Rep's hand-typed observation about a previous conversation gets buried under firmographic data the model already had. The most relevant signal disappears. |
| Suspiciously precise scoring | The model emits 73.4% confidence. The rep does not believe it, and is right not to — the model has no idea why it produced that number. |
| Aggregated-intent noise | Generic intent score collapses 12 different signals into one number. A rep cannot tell whether the lift came from hiring activity or pricing-page visits. |

## Positioning

- **Category claimed**: lead intelligence with explainable scoring for go-to-market teams whose reps have to defend prioritization choices in pipeline reviews.
- **Category refused**: black-box ML lead scoring, "AI SDR" tools that send messages on behalf of humans, generic intent-data resellers, "AI replaces sales team" registers.
- **Closest comparisons**:
  - **Apollo / Clay** — lead-data + workflow tools the copilot is conceptually adjacent to, but adds explainable-scoring discipline as the deliverable contract.
  - **6sense / Demandbase** — intent-data platforms the copilot is conceptually downstream of (consumes their signals as inputs but refuses their black-box aggregation).

---

## Planned MVP

The system the dashboard will graduate to:

- Ingest CRM exports and website-data feeds
- Score leads with transparent factors (typed signals, named recency decay, auditable weights)
- Generate account briefs and outreach angles grounded in the trace
- Track conversion feedback to refine scoring — won/lost outcomes flow back as labels, not as additional opaque signal

**Planned product stack**: Python · FastAPI · Pandas (signal frame) · PostgreSQL (signal ledger + scoring history) · LLMs (brief generation, never scoring).

---

## What ships right now

This is what is in the repo today, audited honestly.

### 1. Showcase dashboard (`/`)

Next.js 14 App Router app at the live URL above. Five routes:

| path | what it shows |
|---|---|
| `/` | Overview — pitch banner, live `/api/stats` Tier-B counters, system status, audience + stack |
| `/prototype` | Product demo — ranked accounts, score trace, CSV schema, and CLI commands for the local scoring MVP |
| `/telemetry` | Polling telemetry consumer — full metric grid, raw JSON, 30s visibility-aware polling, contract docs |
| `/capabilities` | MVP scope, problem statement, why-now, audience, stack — read from `project.json` |
| `/roadmap` | Three-phase timeline (showcase → MVP build → Tier-A graduation) |
| `/settings` | Theme + project metadata |

### 2. Telemetry endpoint (`api/stats.py`)

Stdlib-only Vercel Python serverless function. Reports honest GitHub-derived signals — commits, stars, last commit, primary language, lines of code. Never simulated workload metrics. Contract documented in [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md).

### 3. Python CLI + scoring prototype (`src/revenue_signal_copilot/`)

Argparse-based CLI exposing both the product contract and the first working scoring slice. Product contract commands:

```
revenue-signal-copilot summary       # name, summary, problem, users, stage, track
revenue-signal-copilot capabilities  # planned MVP capabilities
revenue-signal-copilot roadmap       # docs/roadmap.md
```

Working MVP commands:

```
revenue-signal-copilot signal-schema
revenue-signal-copilot score-csv examples/revenue_signals.csv --as-of 2026-05-13
revenue-signal-copilot brief-account examples/revenue_signals.csv --account-id acct-003 --as-of 2026-05-13
revenue-signal-copilot score-csv examples/revenue_signals.csv --as-of 2026-05-13 --format json
```

What the MVP actually does:

- defines a typed signal taxonomy with explicit base weights and half-life decay
- ingests CSV exports with account, signal kind, source, captured date, strength, and summary
- applies recency decay to each signal contribution
- emits a traceable account score
- generates a deterministic account brief grounded in that trace

The CLI still reads `project.json` for the dashboard-facing product contract, but the scoring path is now a real executable prototype instead of a placeholder.

### 4. Deploy + telemetry pipeline

Vercel deploy with `/api/stats` cached 5 minutes, GitHub Actions for the type-check + vitest gate, build-time `_telemetry_static.json` artifact computed by `scripts/compute_telemetry_static.py`.

---

## Architecture (graduation path)

```
┌──── current repo state (showcase-tier) ────────────────────────────┐
│                                                                    │
│  Next.js dashboard ──▶  /api/stats (stdlib Python)  ──▶  GitHub   │
│  (5 routes)              cached 5 min                      API     │
│       │                                                            │
│       └─▶  reads ──▶  project.json  ◀── reads ── Python CLI       │
│                       (typed registry)                             │
└────────────────────────────────────────────────────────────────────┘

                              │  graduates to
                              ▼

┌──── planned MVP (Tier-A) ──────────────────────────────────────────┐
│                                                                    │
│  CRM export ─┐                                                     │
│  Web data ───┼──▶ Signal extractor ──▶ Typed signal ledger        │
│  Rep notes ──┘    (per-source)         (Postgres, with decay)     │
│                                              │                     │
│                                              ▼                     │
│                                        Scoring engine              │
│                                       (named factors, no           │
│                                        black-box ML)               │
│                                              │                     │
│                                              ▼                     │
│                       ┌──────────────────────┴─────────────┐       │
│                       │                                    │       │
│                       ▼                                    ▼       │
│                Defendable trace                    Account brief  │
│              (signal → weight → score)            (LLM, grounded   │
│                                                    in trace)       │
└────────────────────────────────────────────────────────────────────┘
```

The current dashboard is still the public-facing shell. The Python CLI now includes the first real scoring path the future service will extend. `project.json` remains the source of truth for the product registry and showcase metadata.

---

## Quickstart

### Run the showcase dashboard

```bash
git clone https://github.com/IgnazioDS/revenue-signal-copilot.git
cd revenue-signal-copilot
npm install
npm run dev          # http://localhost:3000
```

### Run the Python CLI and local MVP

```bash
cd revenue-signal-copilot
python -m revenue_signal_copilot.cli summary
python -m revenue_signal_copilot.cli capabilities
python -m revenue_signal_copilot.cli roadmap
python -m revenue_signal_copilot.cli signal-schema
python -m revenue_signal_copilot.cli score-csv examples/revenue_signals.csv --as-of 2026-05-13
python -m revenue_signal_copilot.cli brief-account examples/revenue_signals.csv --account-id acct-003 --as-of 2026-05-13
```

### Test + type-check

```bash
npm run lint
npm run type-check
npm test                    # vitest suite
python -m pytest tests/     # python tests
```

---

## Dashboard stack

Next.js 14 App Router · TypeScript strict · Tailwind 3 · Geist Sans + Mono · Radix UI · cmdk (⌘K) · sonner · next-themes · framer-motion · vitest + Testing Library.

### Keyboard shortcuts

| keys | action |
|---|---|
| ⌘K / Ctrl+K | Command palette |
| G then O / T / C / R | Overview / Telemetry / Capabilities / Roadmap |

---

## Prototype scope

What is real now:

- typed revenue signal taxonomy
- CSV-based signal ingestion
- recency-decayed scoring with named factors
- score trace for each account
- deterministic account brief built from the trace

What is still missing:

- CRM and web-data integrations
- a persistent signal ledger
- feedback loops from won/lost outcomes
- API/service packaging around the scoring engine
- LLM-backed brief generation

## More context

- **Operator's hub**: [eleventh.dev](https://eleventh.dev) — the public site this dashboard's telemetry feeds into
- **Reference shipped project**: [NexusRAG](https://github.com/IgnazioDS/NexusRAG) — production-grade multi-tenant RAG agent platform, same operator
- **Telemetry contract**: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md) — what the Tier-B counters mean and what they don't
- **Status of this project**: showcase-tier dashboard plus local scoring MVP. The copilot graduates when the typed signal ledger, integrations, and service layer are live against real GTM data.

---

## License

MIT — see [LICENSE](./LICENSE).
