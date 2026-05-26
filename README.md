# Revenue Signal Copilot

> Lead intelligence with explainable scoring. Every score traces to a named signal a sales rep can defend in a pipeline review — not a number that is suspiciously precise or suspiciously round.

[**Live dashboard →**](https://revenue-signal-copilot.eleventh.dev) · Stage: Ready to build · Track: AI/ML · Category: Business Tool

---

## Status: live public benchmark plus local MVP

**The Python layer is no longer a scaffold, and the public telemetry is now live workload rather than GitHub vanity counters.** Two things ship today.

First, a **local scoring MVP**: a typed signal taxonomy, CSV ingestion, recency-decayed scoring, an explainable trace, and a deterministic account brief. Score your own export with `score-csv`, or explore it at `/prototype`.

Second, a **public daily benchmark**. A scheduled job scores a synthetic, public CRM fixture every day, commits the result back to the repo, and the dashboard serves it. That makes `/api/stats` report Tier-A `mode: "live"` workload metrics, and it powers `/api/scoring-latest` plus the `/scoring` route. The numbers are real computation over a reproducible public fixture. They are never simulated, and never live customer data. See [What ships right now](#what-ships-right-now) and [How the public benchmark scores](#how-the-public-benchmark-scores).

CRM integrations, a persistent signal ledger, and a production multi-tenant service are still not in the repo. For what one of these projects looks like once graduated to production, see [NexusRAG](https://github.com/IgnazioDS/NexusRAG), same operator, same engineering bar, fully shipped.

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

Next.js 14 App Router app at the live URL above. Seven routes:

| path | what it shows |
|---|---|
| `/` | Overview: pitch banner, live `/api/stats` Tier-A scoring metrics, system status, audience + stack |
| `/scoring` | Latest public benchmark run: ranked accounts with expandable score traces, signal mix, precision@K calibration |
| `/prototype` | Product demo: ranked accounts, score trace, CSV schema, and CLI commands for the local scoring MVP |
| `/telemetry` | Polling telemetry consumer: full metric grid, raw JSON, 30s visibility-aware polling, contract docs |
| `/capabilities` | MVP scope, problem statement, why-now, audience, stack, read from `project.json` |
| `/roadmap` | Three-phase timeline (showcase, MVP build, Tier-A graduation) |
| `/settings` | Theme + project metadata |

### 2. Telemetry endpoint (`api/stats.py`), Tier-A live

Stdlib-only Vercel Python serverless function. Reports Tier-A `mode: "live"` workload metrics: `accounts_total`, `accounts_scored_24h`, `signals_detected_24h`, `high_priority_accounts`, plus `uptime_pct_30d` and `last_active_at`. These come from the daily benchmark, not from GitHub counters. The values are real computation over a synthetic, public fixture (`dataset_kind: "synthetic-public"` on `/api/scoring-latest`), so they are reproducible rather than simulated. The function reads a git-committed artifact (`_scoring_latest.json` + `_scoring_history.json`); it never returns 5xx, degrading to zeroed metrics with a contract-valid envelope if the artifact is missing. Contract: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md).

`uptime_pct_30d` is the trailing-30-day scheduled-run success rate: the share of expected daily benchmark runs that completed, since this is a batch system with no socket to ping.

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

Public benchmark command, scoring the synthetic fixture the live dashboard serves:

```
revenue-signal-copilot score --top 5
```

What the MVP actually does:

- defines a typed signal taxonomy with explicit base weights and half-life decay
- ingests CSV exports with account, signal kind, source, captured date, strength, and summary
- applies recency decay to each signal contribution
- emits a traceable account score
- generates a deterministic account brief grounded in that trace

The CLI still reads `project.json` for the dashboard-facing product contract, but the scoring path is now a real executable prototype instead of a placeholder.

### 4. Deploy + benchmark pipeline

Vercel deploy with `/api/stats` and `/api/scoring-latest` behind a short cache. Two GitHub Actions: `python-ci` runs the test gate on every push, and `nightly-scoring` runs the benchmark daily, commits the refreshed `api/_scoring_latest.json` + `api/_scoring_history.json` back to the repo, and lets Vercel redeploy. This is the git-as-database loop: the committed JSON is the only persistence, and the only credential is the workflow's `GITHUB_TOKEN`. Zero secrets, and every data update is an auditable git diff.

### 5. Public scoring benchmark (`src/revenue_signal_copilot/scoring.py`, `scoring_runner.py`)

The engine behind the live `/api/stats` and `/api/scoring-latest`. Scores a 200-account synthetic fixture with per-kind recency decay and a documented score curve, emits a full per-account trace, ranks the top accounts, and calibrates against held-out won/lost labels (precision@K). See [How the public benchmark scores](#how-the-public-benchmark-scores) and [examples/fixtures](./examples/fixtures).

---

## How the public benchmark scores

The `/scoring` page, `/api/scoring-latest`, and Tier-A `/api/stats` are all driven by one engine. Nothing here is a black box; the weights are the contract.

- **Signals are typed.** Four kinds, each with an auditable base-points weight and a half-life (days), set in `KIND_CONFIG`: `job_change` (40 pts, 45d), `infra_shift` (30 pts, 40d), `internal_note` (26 pts, 60d), `hiring` (22 pts, 30d). A `VP+` job change gets a 1.3x seniority multiplier.
- **Recency decays exponentially.** A signal's contribution is `base_points * 0.5 ** (age_days / half_life_days)`. A fresh weak signal can and does outrank a stale strong one. That is the whole thesis.
- **The score is additive, then bounded.** An account's evidence points are the sum of its signal contributions, fully listed in the trace. Up to 70 points the priority score equals the evidence points exactly (it defends itself factor by factor). Above 70 a documented diminishing-returns curve compresses toward 100, so a signal-rich account differentiates from a merely strong one instead of both pinning at the ceiling. An account scoring `>= 70` is "high priority".
- **Calibration is honest.** 50 accounts carry held-out won/lost labels that never feed the score. The benchmark reports precision@20 (share of the top-ranked labeled accounts that converted) against the baseline win rate, so the ranking has to beat chance to look good.
- **It moves daily.** The runner scores as of the run date (so signals age) and injects 1 to 3 date-seeded fresh signals, so each day's run differs and is still reproducible from fixture plus date.

Reproduce any run locally:

```bash
python3 scripts/generate_fixtures.py            # regenerate the public fixture (seeded)
python -m revenue_signal_copilot.cli score      # score it and print the top accounts
python -m revenue_signal_copilot.scoring_runner # write the artifact the endpoints serve
```

---

## Architecture (graduation path)

```
┌──── current repo state ─────────────────────────────────────────────┐
│                                                                      │
│  nightly cron ──▶ scoring_runner ──▶ scores synthetic fixture        │
│       │                                   │                          │
│       │            commits artifact ◀─────┘                          │
│       ▼                                                              │
│  _scoring_latest.json + _scoring_history.json  (git-as-database)     │
│       │                                                              │
│       ├─▶ /api/stats          (Tier-A live)    ──▶ Next.js dashboard │
│       └─▶ /api/scoring-latest (ranked + trace) ──▶ /scoring          │
│                                                                      │
│  your CSV ──▶ copilot.py (score-csv / brief-account) ──▶ /prototype  │
└──────────────────────────────────────────────────────────────────────┘

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

The public benchmark already runs daily and feeds the live telemetry; the local CSV MVP (`copilot.py` / `/prototype`) is the interactive demo of the same idea. Both are the spine the production service will extend: a persistent signal ledger, CRM integrations, and LLM-backed briefs. `project.json` remains the source of truth for the product registry and showcase metadata.

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

### Run the public benchmark

```bash
cd revenue-signal-copilot
python3 scripts/generate_fixtures.py            # regenerate the seeded public fixture
python -m revenue_signal_copilot.cli score      # score it, print the top accounts + traces
python -m revenue_signal_copilot.scoring_runner # write _scoring_latest.json the endpoints serve
```

### Test + type-check

```bash
npm run lint
npm run type-check
npm test                              # vitest suite
python -m unittest discover -s tests  # python tests
```

---

## Dashboard stack

Next.js 14 App Router · TypeScript strict · Tailwind 3 · Geist Sans + Mono · Radix UI · cmdk (⌘K) · sonner · next-themes · framer-motion · vitest + Testing Library.

### Keyboard shortcuts

| keys | action |
|---|---|
| ⌘K / Ctrl+K | Command palette |
| G then O / S / P / T / C / R | Overview / Scoring / Prototype / Telemetry / Capabilities / Roadmap |

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
- **Telemetry contract**: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md), the Tier-A `mode: "live"` envelope this system reports against.
- **Status of this project**: live public benchmark plus local scoring MVP. The copilot graduates when the persistent signal ledger, CRM integrations, and service layer are live against real GTM data.

---

## License

MIT — see [LICENSE](./LICENSE).
