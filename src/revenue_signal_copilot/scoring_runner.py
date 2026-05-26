"""Daily benchmark runner: score the public fixture and publish the artifact.

This is the writer half of the "git-as-database" model. A scheduled GitHub
Action runs ``python -m revenue_signal_copilot.scoring_runner``; the script
scores the committed synthetic fixture as of the run date, appends a summary to
a rolling history, and writes two JSON files under ``api/``:

  - ``_scoring_latest.json``   the full latest run (served by /api/scoring-latest)
  - ``_scoring_history.json``  rolling run summaries (drives uptime + deltas)

The workflow commits those files back to the repo, Vercel redeploys, and the
stdlib endpoints serve them. No database, no secrets.

Two mechanisms keep the public benchmark moving day to day:
  1. Recency decay against the *run date*, so yesterday's signals are a day
     older today and the ranking drifts.
  2. A small date-seeded injection of 1-3 fresh signals, deterministic per day,
     so a third party can reproduce any day's run from fixture + date.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import fixtures
from .scoring import (
    Account,
    AccountScore,
    KIND_CONFIG,
    SIGNAL_KINDS,
    Signal,
    rank,
    score_accounts,
)

SYSTEM_SLUG = "revenue-signal-copilot"
SCHEMA_VERSION = 1
FIXTURE_ID = "synthetic-crm-v1"
DATASET_KIND = "synthetic-public"

TOP_N_DEFAULT = 20
CALIBRATION_K = 20
HISTORY_CAP = 100
RECENT_WINDOW_HOURS = 24

ARTIFACT_FILENAME = "_scoring_latest.json"
HISTORY_FILENAME = "_scoring_history.json"

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUT_DIR = _ROOT / "api"

_INJECT_KINDS = list(SIGNAL_KINDS)


# --- small datetime helpers (kept local so the module is self-contained) -----


def _ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return _ensure_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- daily injection ---------------------------------------------------------


def inject_daily_signals(as_of: datetime, accounts: list[Account]) -> list[Signal]:
    """Deterministic 1-3 fresh signals for ``as_of``, seeded by the date.

    Reproducible: the same date always yields the same injection, so any run is
    auditable from the committed fixture plus the date.
    """
    rng = random.Random(int(_ensure_utc(as_of).strftime("%Y%m%d")))
    count = rng.randint(1, 3)
    chosen = rng.sample(accounts, k=min(count, len(accounts)))
    signals: list[Signal] = []
    for index, account in enumerate(chosen):
        kind = rng.choice(_INJECT_KINDS)
        captured_at = as_of - timedelta(hours=rng.randint(0, 18))
        seniority = rng.choice([None, "Director", "VP+"]) if kind == "job_change" else None
        signals.append(
            Signal(
                signal_id=f"inj_{_ensure_utc(as_of).strftime('%Y%m%d')}_{index}",
                account_id=account.account_id,
                kind=kind,
                source="daily-injection",
                captured_at=captured_at,
                summary="Fresh signal injected by the daily benchmark run.",
                seniority=seniority,
            )
        )
    return signals


# --- calibration -------------------------------------------------------------


def precision_at_k(
    ranked: list[AccountScore], outcomes: dict[str, str], k: int = CALIBRATION_K
) -> float | None:
    """Of the top-``k`` ranked accounts that carry a label, the share that 'won'.

    Returns ``None`` when none of the top-ranked accounts are labeled. The score
    never sees outcomes, so this is a fair test of whether ranking tracks reality.
    """
    labeled = [score for score in ranked if score.account_id in outcomes]
    top = labeled[:k]
    if not top:
        return None
    won = sum(1 for score in top if outcomes[score.account_id] == "won")
    return round(won / len(top), 3)


# --- artifact assembly -------------------------------------------------------


def _recent_signal_count(signals: list[Signal], as_of: datetime) -> int:
    cutoff = _ensure_utc(as_of) - timedelta(hours=RECENT_WINDOW_HOURS)
    end = _ensure_utc(as_of)
    return sum(1 for s in signals if cutoff <= _ensure_utc(s.captured_at) <= end)


def _trace_row(entry: Any) -> dict[str, Any]:
    return {
        "signal_id": entry.signal_id,
        "kind": entry.kind,
        "source": entry.source,
        "captured_at": entry.captured_at,
        "age_days": entry.age_days,
        "base_points": entry.base_points,
        "recency_factor": entry.recency_factor,
        "points": entry.points,
        "reason": entry.reason,
    }


def _ranked_row(position: int, score: AccountScore) -> dict[str, Any]:
    return {
        "rank": position,
        "account_id": score.account_id,
        "name": score.name,
        "industry": score.industry,
        "score": score.score,
        "priority": score.priority,
        "evidence_points": score.raw_points,
        "why": score.why,
        "top_kinds": list(score.top_kinds),
        "trace": [_trace_row(entry) for entry in score.trace],
    }


def _signal_breakdown(signals: list[Signal]) -> list[dict[str, Any]]:
    counts = Counter(s.kind for s in signals)
    total = sum(counts.values()) or 1
    rows = [
        {
            "kind": kind,
            "label": KIND_CONFIG[kind].label,
            "count": counts.get(kind, 0),
            "share": round(counts.get(kind, 0) / total, 3),
        }
        for kind in SIGNAL_KINDS
    ]
    rows.sort(key=lambda row: row["count"], reverse=True)
    return rows


def _previous_delta(
    previous: dict[str, Any] | None, metrics: dict[str, int], ranked: list[AccountScore]
) -> dict[str, Any] | None:
    if not previous:
        return None
    prev_high = previous.get("metrics", {}).get("high_priority_accounts")
    delta_high = (
        metrics["high_priority_accounts"] - prev_high
        if isinstance(prev_high, int)
        else None
    )
    top_id = ranked[0].account_id if ranked else None
    prev_top_id = previous.get("top_account_id")
    return {
        "run_id": previous.get("run_id"),
        "generated_at": previous.get("generated_at"),
        "delta": {
            "high_priority_accounts": delta_high,
            "top_account_changed": prev_top_id is not None and prev_top_id != top_id,
            "top_account": ranked[0].name if ranked else None,
        },
    }


def build_artifact(
    as_of: datetime,
    accounts: list[Account],
    signals: list[Signal],
    outcomes: dict[str, str],
    previous: dict[str, Any] | None = None,
    top_n: int = TOP_N_DEFAULT,
) -> dict[str, Any]:
    """Assemble the published scoring artifact. Pure given its inputs."""
    scores = score_accounts(accounts, signals, as_of)
    ranked_all = rank(scores)
    ranked_top = ranked_all[:top_n]

    metrics = {
        "accounts_total": len(accounts),
        "accounts_scored_24h": len(accounts),
        "signals_detected_24h": _recent_signal_count(signals, as_of),
        "high_priority_accounts": sum(1 for s in scores if s.priority == "high"),
    }

    won = sum(1 for outcome in outcomes.values() if outcome == "won")
    calibration = {
        "metric": f"precision_at_{CALIBRATION_K}",
        "k": CALIBRATION_K,
        "precision": precision_at_k(ranked_all, outcomes, k=CALIBRATION_K),
        "baseline_win_rate": round(won / len(outcomes), 3) if outcomes else None,
        "labeled_accounts": len(outcomes),
        "note": (
            "Share of the top-ranked labeled accounts that converted (won). "
            "Baseline is the overall win rate across all labels. Outcomes are "
            "never a scoring input."
        ),
    }

    timestamp = _iso(as_of)
    return {
        "system": SYSTEM_SLUG,
        "mode": "live",
        "status": "operational",
        "run_id": f"rsc-{_ensure_utc(as_of).strftime('%Y%m%dT%H%M%SZ')}",
        "fixture": FIXTURE_ID,
        "dataset_kind": DATASET_KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "as_of": timestamp,
        "metrics": metrics,
        "calibration": calibration,
        "ranked_accounts": [
            _ranked_row(position, score)
            for position, score in enumerate(ranked_top, start=1)
        ],
        "top_signals": _signal_breakdown(signals),
        "previous_run": _previous_delta(previous, metrics, ranked_all),
    }


# --- persistence (git-as-database) -------------------------------------------


def _out_dir(out_dir: Path | str | None) -> Path:
    return Path(out_dir) if out_dir is not None else _DEFAULT_OUT_DIR


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # indent=2 keeps the committed artifact diff-readable: every daily run is a
    # legible git diff, which is the whole point of git-as-database.
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_history(out_dir: Path | str | None = None) -> dict[str, Any]:
    path = _out_dir(out_dir) / HISTORY_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("runs"), list):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        pass
    return {"system": SYSTEM_SLUG, "schema_version": SCHEMA_VERSION, "runs": []}


def _history_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    ranked = artifact["ranked_accounts"]
    top = ranked[0] if ranked else {}
    return {
        "run_id": artifact["run_id"],
        "generated_at": artifact["generated_at"],
        "as_of": artifact["as_of"],
        "metrics": artifact["metrics"],
        "top_account_id": top.get("account_id"),
        "top_account_name": top.get("name"),
        "calibration_precision": artifact["calibration"]["precision"],
    }


def _append_history(
    history: dict[str, Any], artifact: dict[str, Any], out_dir: Path
) -> None:
    history.setdefault("system", SYSTEM_SLUG)
    history.setdefault("schema_version", SCHEMA_VERSION)
    history["runs"].append(_history_summary(artifact))
    history["runs"] = history["runs"][-HISTORY_CAP:]
    _write_json(out_dir / HISTORY_FILENAME, history)


def run(
    as_of: datetime | None = None,
    top_n: int = TOP_N_DEFAULT,
    fixtures_dir: Path | str | None = None,
    out_dir: Path | str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Score the fixture as of ``as_of`` (default now) and publish the artifact."""
    as_of = as_of or datetime.now(timezone.utc)
    target = _out_dir(out_dir)

    accounts = fixtures.load_accounts(fixtures_dir)
    signals = fixtures.load_signals(fixtures_dir) + inject_daily_signals(as_of, accounts)
    outcomes = fixtures.load_outcomes(fixtures_dir)

    history = load_history(target)
    previous = history["runs"][-1] if history["runs"] else None
    artifact = build_artifact(as_of, accounts, signals, outcomes, previous, top_n)

    if write:
        _write_json(target / ARTIFACT_FILENAME, artifact)
        _append_history(history, artifact, target)
    return artifact


def main(argv: list[str] | None = None) -> int:
    artifact = run()
    metrics = artifact["metrics"]
    calibration = artifact["calibration"]
    print(
        f"scored {metrics['accounts_total']} accounts; "
        f"{metrics['high_priority_accounts']} high-priority; "
        f"precision@{calibration['k']}={calibration['precision']} "
        f"(baseline {calibration['baseline_win_rate']}); "
        f"run_id {artifact['run_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
