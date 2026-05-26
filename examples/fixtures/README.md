# Public scoring fixture

This directory holds the **synthetic, public CRM fixture** the daily scoring
benchmark runs against. It is the dataset behind the Tier-A `/api/stats` and
`/api/scoring-latest` numbers on the live deploy.

It contains **no real companies, no PII, and no customer data**. Every row is
generated deterministically by `scripts/generate_fixtures.py`. The point is
reproducibility: anyone can regenerate these exact files and re-run the scoring
locally to audit how a number was produced.

## Reproduce

```bash
python3 scripts/generate_fixtures.py     # rewrites the three files below
python3 -m revenue_signal_copilot.cli score    # score them and print the top accounts
```

Generation is pinned by `SEED = 11` and `REFERENCE_DATE = 2026-05-26` in the
generator, so the output is byte-stable across machines and across calendar
time. Timestamps are anchored to `REFERENCE_DATE` (not wall-clock now); the
scoring runner ages signals against its own run date, which is what produces
day-to-day movement in the public benchmark.

## Files

### `crm-accounts.csv` — 200 accounts

| column | meaning |
|---|---|
| `account_id` | stable id, `acct_0000` .. `acct_0199` |
| `name` | generated company name (not a real company) |
| `industry` | one of 10 industries |
| `employee_count` | size bucket |
| `region` | `NA` / `EMEA` / `APAC` / `LATAM` |
| `created_at` | account-created timestamp (ISO-8601) |

### `signals-typed.jsonl` — 911 typed signals

One JSON object per line:

```json
{"signal_id":"sig_00000","account_id":"acct_0007","kind":"job_change","source":"linkedin","captured_at":"2026-05-20T14:31:00Z","summary":"New VP Engineering hired","seniority":"VP+"}
```

`kind` is one of `job_change`, `hiring`, `infra_shift`, `internal_note`.
`seniority` is present only on some `job_change` signals (`VP+` / `Director`).
`captured_at` is recency-skewed: most signals are recent, with a long tail out
to ~18 months, so the recency-decay model has something to discriminate.

### `outcomes-labels.csv` — 50 labels (22 won / 28 lost)

| column | meaning |
|---|---|
| `account_id` | account this outcome belongs to |
| `outcome` | `won` or `lost` |
| `labeled_at` | when the outcome was recorded (ISO-8601) |

**Outcomes are used only to calibrate the benchmark** (precision@K: do the
top-ranked accounts correlate with `won`?). They are never fed back into the
score as an input. Labels are biased toward `won` for accounts with stronger,
fresher signals, using a propensity proxy that is deliberately independent of
the scoring engine, so precision@K is a fair test rather than a tautology.

## How a score is produced

The weights and the recency half-lives are the auditable contract; see the
"How scoring works" section of the repo `README.md`. Nothing here is a black
box: `score` is a documented function of the signal contributions listed in
each account's trace.
