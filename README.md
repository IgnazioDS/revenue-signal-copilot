# Revenue Signal Copilot

> Lead intelligence with explainable scoring. Every score traces to a named signal a sales rep can defend in a pipeline review — not a number that is suspiciously precise or suspiciously round.

[**Live dashboard →**](https://revenue-signal-copilot.eleventh.dev) · Stage: Ready to build · Track: AI/ML · Category: Business Tool

---

## Status: showcase-state

**This repository is in showcase-state.** The copilot itself — the signal taxonomy, the scoring engine, the trace generator, the CRM integrations — is not yet in this repo. What ships now is a public dashboard, a stdlib-only telemetry endpoint, and a Python CLI scaffold that exposes the project contract. See [What ships right now](#what-ships-right-now) for the audit.

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
| `/telemetry` | Polling telemetry consumer — full metric grid, raw JSON, 30s visibility-aware polling, contract docs |
| `/capabilities` | MVP scope, problem statement, why-now, audience, stack — read from `project.json` |
| `/roadmap` | Three-phase timeline (showcase → MVP build → Tier-A graduation) |
| `/settings` | Theme + project metadata |

### 2. Telemetry endpoint (`api/stats.py`)

Stdlib-only Vercel Python serverless function. Reports honest GitHub-derived signals — commits, stars, last commit, primary language, lines of code. Never simulated workload metrics. Contract documented in [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md).

### 3. Python CLI scaffold (`src/revenue_signal_copilot/`)

Argparse-based CLI exposing the project contract. Currently three subcommands:

```
revenue-signal-copilot summary       # name, summary, problem, users, stage, track
revenue-signal-copilot capabilities  # planned MVP capabilities
revenue-signal-copilot roadmap       # docs/roadmap.md
```

The CLI reads `project.json` — a typed registry that drives the dashboard's `/capabilities` route and the CLI. When MVP work begins, the signal taxonomy and scoring engine layer onto this scaffold.

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

The current dashboard is the public-facing shell. The Python CLI is the spine the MVP copilot will extend. `project.json` stays as the single source of truth for what the system claims to be.

---

## Quickstart

### Run the showcase dashboard

```bash
git clone https://github.com/IgnazioDS/revenue-signal-copilot.git
cd revenue-signal-copilot
npm install
npm run dev          # http://localhost:3000
```

### Run the Python CLI scaffold

```bash
cd revenue-signal-copilot
python -m revenue_signal_copilot.cli summary
python -m revenue_signal_copilot.cli capabilities
python -m revenue_signal_copilot.cli roadmap
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

## More context

- **Operator's hub**: [eleventh.dev](https://eleventh.dev) — the public site this dashboard's telemetry feeds into
- **Reference shipped project**: [NexusRAG](https://github.com/IgnazioDS/NexusRAG) — production-grade multi-tenant RAG agent platform, same operator
- **Telemetry contract**: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md) — what the Tier-B counters mean and what they don't
- **Status of this project**: showcase-tier. The copilot graduates when the typed signal ledger and the explainable scoring trace are live against a real GTM dataset.

---

## License

MIT — see [LICENSE](./LICENSE).
