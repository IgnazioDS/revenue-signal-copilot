"""Loaders for the public synthetic CRM fixture.

The fixture lives in ``examples/fixtures/`` at the repo root, is generated
deterministically by ``scripts/generate_fixtures.py``, and is committed so any
third party can reproduce a scoring run locally. These loaders parse the
committed files back into the engine's typed domain objects.

Stdlib only: this code runs in CI and (transitively) anywhere the package is
installed, so it carries no dependency footprint.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .scoring import Account, Signal

# repo_root / src / revenue_signal_copilot / fixtures.py  ->  parents[2] == root
_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _REPO_ROOT / "examples" / "fixtures"

ACCOUNTS_FILE = "crm-accounts.csv"
SIGNALS_FILE = "signals-typed.jsonl"
OUTCOMES_FILE = "outcomes-labels.csv"


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Accepts a trailing ``Z`` (which ``datetime.fromisoformat`` rejects before
    Python 3.11). Naive inputs are assumed UTC.
    """
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _fixtures_dir(override: Path | str | None) -> Path:
    return Path(override) if override is not None else FIXTURES_DIR


def load_accounts(fixtures_dir: Path | str | None = None) -> list[Account]:
    path = _fixtures_dir(fixtures_dir) / ACCOUNTS_FILE
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        Account(
            account_id=row["account_id"],
            name=row["name"],
            industry=row["industry"],
            employee_count=int(row["employee_count"]),
            region=row["region"],
        )
        for row in rows
    ]


def load_signals(fixtures_dir: Path | str | None = None) -> list[Signal]:
    path = _fixtures_dir(fixtures_dir) / SIGNALS_FILE
    signals: list[Signal] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            signals.append(
                Signal(
                    signal_id=record["signal_id"],
                    account_id=record["account_id"],
                    kind=record["kind"],
                    source=record["source"],
                    captured_at=parse_iso(record["captured_at"]),
                    summary=record.get("summary", ""),
                    seniority=record.get("seniority"),
                )
            )
    return signals


def load_outcomes(fixtures_dir: Path | str | None = None) -> dict[str, str]:
    """Return {account_id: outcome} where outcome is 'won' or 'lost'.

    Used only for benchmark calibration (precision@K), never as a scoring input.
    """
    path = _fixtures_dir(fixtures_dir) / OUTCOMES_FILE
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["account_id"]: row["outcome"] for row in csv.DictReader(handle)}
