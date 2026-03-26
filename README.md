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
