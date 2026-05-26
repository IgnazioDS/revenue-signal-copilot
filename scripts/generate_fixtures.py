"""Generate the public synthetic CRM fixture for the scoring benchmark.

Deterministic and stdlib-only. Re-running with the same SEED and REFERENCE_DATE
reproduces byte-identical files, so the committed fixture is auditable and any
third party can regenerate it:

    python3 scripts/generate_fixtures.py

Writes to examples/fixtures/:
  - crm-accounts.csv      (~200 accounts)
  - signals-typed.jsonl   (~1000 typed signals across 4 kinds, recency-skewed)
  - outcomes-labels.csv   (~50 won/lost labels, biased by signal propensity)

Timestamps are anchored to REFERENCE_DATE (not wall-clock now) so the data is
stable across calendar time; the scoring runner ages signals against its own
run date, which is what creates day-to-day movement in the public benchmark.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "examples" / "fixtures"

SEED = 11  # nod to "eleventh"; fixes the entire generation
REFERENCE_DATE = datetime(2026, 5, 26, tzinfo=timezone.utc)
N_ACCOUNTS = 200
N_OUTCOMES = 50
MAX_SIGNAL_AGE_DAYS = 540  # ~18 months; the stale end of the recency spectrum

NAME_PREFIXES = [
    "North", "Blue", "Iron", "Summit", "Cedar", "Vertex", "Quant", "Pine",
    "Harbor", "Granite", "Silver", "Copper", "Crest", "Atlas", "Nova", "Orbit",
    "Delta", "Ridge", "Birch", "Falcon", "Onyx", "Aspen", "Cobalt", "Maple",
]
NAME_ROOTS = [
    "wind", "wave", "field", "gate", "river", "stone", "peak", "fork", "line",
    "bridge", "point", "spark", "loop", "shore", "vale", "grove",
]
NAME_SUFFIXES = [
    "Logistics", "Labs", "Systems", "Group", "Networks", "Analytics", "Dynamics",
    "Works", "Health", "Capital", "Robotics", "Foods", "Retail", "Media",
    "Software", "Industries",
]
INDUSTRIES = [
    "SaaS", "Logistics", "Fintech", "Healthcare", "Manufacturing", "Retail",
    "Media", "Energy", "EdTech", "Real Estate",
]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]

# kind -> (relative weight in the population, candidate sources, summary templates)
SIGNAL_KINDS = {
    "job_change": (
        0.28,
        ["linkedin", "clearbit", "crunchbase"],
        ["New {role} hired", "{role} joined from competitor", "Leadership change: {role}"],
    ),
    "hiring": (
        0.30,
        ["greenhouse", "lever", "careers-page"],
        ["Opened {n} {team} roles", "Hiring spike in {team}", "Backfilling {team}"],
    ),
    "infra_shift": (
        0.24,
        ["builtwith", "wappalyzer", "dns-records"],
        ["Adopted {tech}", "Migrated to {tech}", "Detected {tech} in stack"],
    ),
    "internal_note": (
        0.18,
        ["rep-note", "call-log", "email-thread"],
        ["Rep flagged budget approved", "Champion identified", "Asked for pricing"],
    ),
}
ROLES = ["VP Engineering", "Head of Data", "CTO", "VP Sales", "Director of RevOps"]
TEAMS = ["data", "platform", "growth", "security", "sales engineering"]
TECHS = ["Snowflake", "dbt", "Kubernetes", "Segment", "Databricks", "pgvector"]
SENIORITY_CHOICES = [None, None, "Director", "VP+"]  # job_change skews senior-ish


def _company_names(rng: random.Random, count: int) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    while len(names) < count:
        name = (
            f"{rng.choice(NAME_PREFIXES)}{rng.choice(NAME_ROOTS)} "
            f"{rng.choice(NAME_SUFFIXES)}"
        )
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _recency_days(rng: random.Random) -> int:
    """Recency-skewed age: most signals recent, with a long stale tail."""
    age = int(rng.expovariate(1 / 120))  # mean ~120 days
    return min(age, MAX_SIGNAL_AGE_DAYS)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_signal(rng: random.Random, sid: int, account_id: str) -> dict:
    kind = rng.choices(
        list(SIGNAL_KINDS), weights=[meta[0] for meta in SIGNAL_KINDS.values()]
    )[0]
    _, sources, templates = SIGNAL_KINDS[kind]
    age = _recency_days(rng)
    captured_at = REFERENCE_DATE - timedelta(
        days=age, hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
    )
    summary = rng.choice(templates).format(
        role=rng.choice(ROLES), n=rng.randint(2, 9),
        team=rng.choice(TEAMS), tech=rng.choice(TECHS),
    )
    record = {
        "signal_id": f"sig_{sid:05d}",
        "account_id": account_id,
        "kind": kind,
        "source": rng.choice(sources),
        "captured_at": _iso(captured_at),
        "summary": summary,
    }
    if kind == "job_change":
        seniority = rng.choice(SENIORITY_CHOICES)
        if seniority is not None:
            record["seniority"] = seniority
    return record


def _propensity(signals: list[dict]) -> float:
    """Cheap proxy used only to bias outcome labels: recent signals count more.

    Independent of the scoring engine (no import) so calibration is a fair test,
    yet correlated enough that precision@K beats random.
    """
    score = 0.0
    for sig in signals:
        age = (REFERENCE_DATE - datetime.fromisoformat(
            sig["captured_at"].replace("Z", "+00:00")
        )).days
        score += max(0.0, 1.0 - age / MAX_SIGNAL_AGE_DAYS)
    return score


def generate() -> dict[str, int]:
    rng = random.Random(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    names = _company_names(rng, N_ACCOUNTS)
    accounts = []
    for i, name in enumerate(names):
        accounts.append({
            "account_id": f"acct_{i:04d}",
            "name": name,
            "industry": rng.choice(INDUSTRIES),
            "employee_count": rng.choice([25, 50, 120, 240, 500, 1200, 3000]),
            "region": rng.choice(REGIONS),
            "created_at": _iso(REFERENCE_DATE - timedelta(days=rng.randint(365, 2200))),
        })

    signals_by_account: dict[str, list[dict]] = {a["account_id"]: [] for a in accounts}
    sid = 0
    for account in accounts:
        # Per-account signal count averages ~5, a few accounts are signal-rich.
        n_signals = max(0, int(rng.gauss(5, 3)))
        for _ in range(n_signals):
            signal = _make_signal(rng, sid, account["account_id"])
            signals_by_account[account["account_id"]].append(signal)
            sid += 1

    all_signals = [s for sigs in signals_by_account.values() for s in sigs]

    # Outcome labels: sample 50 accounts, bias 'won' by signal propensity.
    propensities = {a["account_id"]: _propensity(signals_by_account[a["account_id"]])
                    for a in accounts}
    max_prop = max(propensities.values()) or 1.0
    labeled_ids = rng.sample([a["account_id"] for a in accounts], N_OUTCOMES)
    outcomes = []
    for account_id in sorted(labeled_ids):
        win_prob = 0.18 + 0.62 * (propensities[account_id] / max_prop)
        outcome = "won" if rng.random() < win_prob else "lost"
        outcomes.append({
            "account_id": account_id,
            "outcome": outcome,
            "labeled_at": _iso(REFERENCE_DATE - timedelta(days=rng.randint(10, 200))),
        })

    _write_accounts(accounts)
    _write_signals(all_signals)
    _write_outcomes(outcomes)

    won = sum(1 for o in outcomes if o["outcome"] == "won")
    return {
        "accounts": len(accounts),
        "signals": len(all_signals),
        "outcomes": len(outcomes),
        "won": won,
        "lost": len(outcomes) - won,
    }


def _write_accounts(accounts: list[dict]) -> None:
    fields = ["account_id", "name", "industry", "employee_count", "region", "created_at"]
    with (OUT_DIR / "crm-accounts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(accounts)


def _write_signals(signals: list[dict]) -> None:
    with (OUT_DIR / "signals-typed.jsonl").open("w", encoding="utf-8") as handle:
        for signal in signals:
            handle.write(json.dumps(signal, separators=(",", ":")) + "\n")


def _write_outcomes(outcomes: list[dict]) -> None:
    fields = ["account_id", "outcome", "labeled_at"]
    with (OUT_DIR / "outcomes-labels.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(outcomes)


def main() -> int:
    counts = generate()
    rel = OUT_DIR.relative_to(ROOT)
    print(f"wrote fixture to {rel}/")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
