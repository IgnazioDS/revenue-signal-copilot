# Revenue Signal Copilot

A lead intelligence and prioritization system that scores accounts using public signals and internal notes.

## Problem

Outbound teams chase low-signal leads because enrichment and prioritization are fragmented across tools.

## Users

Sales teams, agencies, founder-led GTM teams

## Core Capabilities

- Ingest CRM exports and website data
- Score leads with transparent factors
- Generate account briefs and outreach angles
- Track conversion feedback to refine scoring

## Why This Matters

Small teams need leverage from AI systems that can turn scattered signals into action.

## Architecture

- `core`: domain logic for revenue signal copilot.
- `cli`: operator-facing entrypoint for local workflows and smoke checks.
- `docs/`: product notes, roadmap, and architecture decisions.
- `tests/`: baseline regression coverage for the project contract.

## Local Usage

```bash
uv run revenue-signal-copilot summary
uv run revenue-signal-copilot capabilities
uv run revenue-signal-copilot roadmap
```

## Initial Stack Direction

Python, FastAPI, Pandas, PostgreSQL, LLMs

## Delivery Standard

- Clear product thesis
- Setup that works locally
- Tests for the primary contract
- Documentation for roadmap and architecture
- Space for production integrations in the next iteration

## Showcase

This repository ships with a static Vercel-ready landing page for demos and previews.

```bash
vercel deploy -y
```

The deployed site presents Revenue Signal Copilot as a standalone product page.

## Production telemetry

This deployment exposes public, aggregate metrics at `/api/stats`. The endpoint
is consumed by the Production Telemetry panel on https://eleventh.dev. The
schema is documented at
https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md.

This system is in **showcase mode** — the Vercel deploy is a public landing
page, not a system processing production workload. The endpoint exposes real
GitHub-derived metrics about the codebase rather than fabricated activity
counters. Tier-A workload metrics (`accounts_scored_24h`, `signals_detected_24h`,
`high_priority_accounts`, etc.) are added when the system is promoted from
showcase to production.

Sample response:

```bash
$ curl -i https://revenue-signal-copilot.vercel.app/api/stats
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=30, stale-while-revalidate=60
Access-Control-Allow-Origin: *

{
  "system": "revenue-signal-copilot",
  "mode": "showcase",
  "status": "operational",
  "last_deployed_at": "2026-04-27T18:41:58Z",
  "last_commit_at": "2026-04-01T18:29:59Z",
  "metrics": {
    "commits_30d": 1,
    "commits_total": 3,
    "primary_language": "Python",
    "repo_stars": 0,
    "lines_of_code": 1178
  },
  "schema_version": 1,
  "generated_at": "2026-04-27T18:42:27Z"
}
```

The endpoint never returns HTTP 5xx. If GitHub is unreachable, the response
status flips to `"degraded"` and metric values fall back to last known good
(or zero) values, while the JSON contract remains valid.

To regenerate `lines_of_code` before deploying:

```bash
python3 scripts/compute_telemetry_static.py
git add api/_telemetry_static.json
```
