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
- `cli.py` exposes showcase commands, the CSV scoring MVP commands, and the public-benchmark `score` command.
- `copilot.py` is the local CSV MVP: typed signal taxonomy, CSV ingestion, recency decay, score trace, and brief generation.
- `scoring.py` is the public-benchmark engine: typed signals, per-kind recency decay, additive evidence points with a diminishing-returns knee, and an auditable trace.
- `fixtures.py` loads the committed synthetic fixture; `scripts/generate_fixtures.py` generates it deterministically.
- `scoring_runner.py` scores the fixture and writes the committed artifact (`api/_scoring_latest.json` + `api/_scoring_history.json`) the endpoints serve.

## Current MVP Flow

The local prototype now runs this path:

1. Read a CSV export of account signals.
2. Validate each row against a typed signal taxonomy.
3. Apply base weights plus half-life decay per signal kind.
4. Aggregate the resulting signal contributions into an account score.
5. Render both a score trace and a deterministic account brief.

This is intentionally local-first and stdlib-only. The point of the slice is to prove the scoring contract before the repo grows a service boundary or CRM integrations.

## Public Benchmark Flow (git-as-database)

The live telemetry runs a separate, always-on path with no database and no secrets:

1. A daily GitHub Action runs `scoring_runner` against the committed synthetic fixture, as of the run date plus a small date-seeded injection so the result moves day to day.
2. The runner writes `api/_scoring_latest.json` (full run: ranked accounts, traces, calibration, previous-run delta) and appends to `api/_scoring_history.json` (rolling 100 runs).
3. The Action commits those files back to the repo. Vercel redeploys on the push.
4. Stdlib serverless functions read the committed JSON: `api/stats.py` serves the Tier-A envelope, `api/scoring-latest.py` serves the full run. Neither makes a network call or holds a secret.

The committed artifact is the persistence layer. Every daily update is a reviewable git diff, which is what makes the benchmark auditable.
