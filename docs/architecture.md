# Architecture Notes

## Product Shape

Revenue Signal Copilot starts as a focused Python service or CLI with a clean domain boundary. The local interface is intentionally small so the core logic can evolve into an API, worker, or scheduled job without rework.

## Design Priorities

- Keep the product contract explicit and testable.
- Avoid framework lock-in early.
- Reserve room for persistence, telemetry, and deployment concerns.
- Treat generated output as an artifact that can be audited.

## Current Modules

- `models.py` defines the typed project metadata.
- `catalog.py` loads the shipped product spec.
- `cli.py` exposes both showcase commands and MVP scoring commands.
- `copilot.py` contains the typed signal taxonomy, CSV ingestion, recency decay, score trace, and brief generation.

## Current MVP Flow

The local prototype now runs this path:

1. Read a CSV export of account signals.
2. Validate each row against a typed signal taxonomy.
3. Apply base weights plus half-life decay per signal kind.
4. Aggregate the resulting signal contributions into an account score.
5. Render both a score trace and a deterministic account brief.

This is intentionally local-first and stdlib-only. The point of the slice is to prove the scoring contract before the repo grows a service boundary or CRM integrations.
