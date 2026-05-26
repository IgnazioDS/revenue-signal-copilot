"""Explainable account-scoring engine.

This is the spine the showcase scaffold graduates onto. It scores accounts from
typed signals using named, auditable weights and per-kind recency decay, and
emits a trace a sales rep can defend in a pipeline review.

Design contract (from the product thesis in README.md):

- **Additive, not black-box.** A score is the sum of its signal contributions,
  capped at 100. The trace lists every contribution, so the number defends
  itself: ``84 = job-change (40) + infra-shift (28) + note (16)``.
- **Recency dominates.** Each signal kind decays on its own half-life, so a
  fresh weak signal overtakes a stale strong one. An 18-month-old signal
  weighted equal to a 7-day-old one is the failure this engine refuses to make.
- **Pure and deterministic.** Same inputs always produce an identical, frozen
  result. No randomness, no hidden state, stdlib only.

All weights live in :data:`KIND_CONFIG` and are documented in the README so any
third party can audit how a number was produced.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

# --- taxonomy ---------------------------------------------------------------

SIGNAL_KINDS: tuple[str, ...] = ("job_change", "infra_shift", "hiring", "internal_note")


@dataclass(frozen=True)
class SignalKindConfig:
    """Auditable weights for a signal kind.

    ``base_points`` is the contribution at age zero. ``half_life_days`` is how
    many days it takes for that contribution to halve under recency decay.
    """

    base_points: float
    half_life_days: float
    label: str


# The single source of truth for "how a score is produced". Tuned so that
# recency outranks raw quality: a fresh hiring post (25) beats an 18-month
# job-change (45) once decay is applied. See tests/test_scoring.py.
KIND_CONFIG: dict[str, SignalKindConfig] = {
    "job_change": SignalKindConfig(40.0, 45.0, "job-change event"),
    "infra_shift": SignalKindConfig(30.0, 40.0, "infrastructure shift"),
    "internal_note": SignalKindConfig(26.0, 60.0, "internal rep note"),
    "hiring": SignalKindConfig(22.0, 30.0, "hiring activity"),
}

# A job-change at senior level matters more. Applied multiplicatively to the
# base points so the trace still shows a single, explainable contribution.
SENIORITY_BONUS: dict[str, float] = {"VP+": 1.30, "Director": 1.10}

HIGH_PRIORITY_THRESHOLD: int = 70  # score >= this is surfaced as "high"
WATCH_THRESHOLD: int = 40  # score >= this is "watch"; below is "low"
SCORE_CAP: int = 100

# Evidence points (the additive sum of signal contributions) map onto the 0-100
# priority score through a diminishing-returns knee. Below KNEE_RAW the mapping
# is the identity, so a typical account's score IS the sum of its trace points
# and defends itself factor by factor. Above the knee the score compresses
# asymptotically toward 100, so a signal-rich account differentiates from a
# merely strong one instead of both pinning at the ceiling. One monotonic curve,
# documented in the README, never a black box.
KNEE_RAW: float = 70.0
COMPRESSION_SCALE: float = 40.0  # larger = gentler compression above the knee

_DAY_SECONDS: float = 86_400.0


# --- domain types -----------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """A typed, time-stamped signal about an account."""

    signal_id: str
    account_id: str
    kind: str
    source: str
    captured_at: datetime
    summary: str = ""
    seniority: str | None = None


@dataclass(frozen=True)
class Account:
    account_id: str
    name: str
    industry: str
    employee_count: int
    region: str


@dataclass(frozen=True)
class TraceEntry:
    """One signal's audited contribution to an account's score."""

    signal_id: str
    kind: str
    source: str
    captured_at: str
    age_days: float
    base_points: float
    recency_factor: float
    points: float
    reason: str


@dataclass(frozen=True)
class AccountScore:
    account_id: str
    name: str
    industry: str
    score: int
    raw_points: float
    priority: str
    trace: tuple[TraceEntry, ...]
    why: str
    top_kinds: tuple[str, ...]


# --- pure helpers -----------------------------------------------------------


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so age math never mixes aware and naive."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return _as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_kind(kind: str) -> None:
    if kind not in KIND_CONFIG:
        raise ValueError(
            f"Unknown signal kind: {kind!r}. Expected one of {SIGNAL_KINDS}."
        )


def recency_factor(age_days: float, half_life_days: float) -> float:
    """Exponential decay: 1.0 fresh, 0.5 at one half-life, monotone decreasing."""
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def age_in_days(captured_at: datetime, as_of: datetime) -> float:
    return (_as_utc(as_of) - _as_utc(captured_at)).total_seconds() / _DAY_SECONDS


def priority_score(raw_points: float) -> int:
    """Map additive evidence points onto a bounded 0-100 priority score.

    Identity below :data:`KNEE_RAW` (the score equals the evidence points), then
    a smooth exponential compression that approaches but never exceeds 100.
    Monotonic increasing, so more evidence never lowers the score.
    """
    if raw_points <= KNEE_RAW:
        return max(0, round(raw_points))
    headroom = SCORE_CAP - KNEE_RAW
    compressed = KNEE_RAW + headroom * (
        1.0 - math.exp(-(raw_points - KNEE_RAW) / COMPRESSION_SCALE)
    )
    return min(SCORE_CAP, round(compressed))


def priority_for(score: int) -> str:
    if score >= HIGH_PRIORITY_THRESHOLD:
        return "high"
    if score >= WATCH_THRESHOLD:
        return "watch"
    return "low"


def _humanize_age(age_days: float) -> str:
    days = int(round(age_days))
    if days <= 0:
        return "today"
    if days == 1:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        months = max(1, round(days / 30))
        return "about 1 month ago" if months == 1 else f"about {months} months ago"
    years = round(days / 365, 1)
    return f"about {years:g} years ago"


def _reason(config: SignalKindConfig, age_days: float, signal: Signal) -> str:
    seniority = f" at {signal.seniority}" if signal.seniority else ""
    return f"{config.label}{seniority} {_humanize_age(age_days)}"


def _trace_entry(signal: Signal, as_of: datetime) -> TraceEntry:
    _validate_kind(signal.kind)
    config = KIND_CONFIG[signal.kind]
    age = age_in_days(signal.captured_at, as_of)
    factor = recency_factor(max(age, 0.0), config.half_life_days)
    base = config.base_points * SENIORITY_BONUS.get(signal.seniority or "", 1.0)
    points = round(base * factor, 2)
    return TraceEntry(
        signal_id=signal.signal_id,
        kind=signal.kind,
        source=signal.source,
        captured_at=_iso(signal.captured_at),
        age_days=round(age, 1),
        base_points=round(base, 2),
        recency_factor=round(factor, 4),
        points=points,
        reason=_reason(config, age, signal),
    )


def _compose_why(
    account: Account, score: int, raw_points: float, trace: Sequence[TraceEntry]
) -> str:
    """A one-line defense of the score.

    Cites the score, the total evidence points (which the trace table sums to
    exactly), and names the top contributing signals. It never implies the named
    factors add up to the score, because above the knee they do not: the trace
    is the audit, this sentence is the headline.
    """
    if not trace:
        return f"{account.name} scored {score}/100 on 0 evidence points: no active signals."
    top = trace[:3]
    factors = ", ".join(entry.reason for entry in top)
    extra = len(trace) - len(top)
    tail = f", plus {extra} more" if extra > 0 else ""
    return (
        f"{account.name} scored {score}/100 on {round(raw_points)} evidence "
        f"points: {factors}{tail}."
    )


# --- public API -------------------------------------------------------------


def score_account(
    account: Account, signals: Iterable[Signal], as_of: datetime
) -> AccountScore:
    """Score one account from its signals as of ``as_of``.

    Signals for other accounts are ignored, so the caller may pass a superset.
    """
    entries = [
        _trace_entry(signal, as_of)
        for signal in signals
        if signal.account_id == account.account_id
    ]
    entries.sort(key=lambda entry: entry.points, reverse=True)
    raw = round(sum(entry.points for entry in entries), 2)
    score = priority_score(raw)
    return AccountScore(
        account_id=account.account_id,
        name=account.name,
        industry=account.industry,
        score=score,
        raw_points=raw,
        priority=priority_for(score),
        trace=tuple(entries),
        why=_compose_why(account, score, raw, entries),
        top_kinds=tuple(dict.fromkeys(entry.kind for entry in entries[:3])),
    )


def score_accounts(
    accounts: Iterable[Account], signals: Iterable[Signal], as_of: datetime
) -> list[AccountScore]:
    """Score many accounts in one pass, bucketing signals by account first."""
    by_account: dict[str, list[Signal]] = {}
    for signal in signals:
        by_account.setdefault(signal.account_id, []).append(signal)
    return [
        score_account(account, by_account.get(account.account_id, ()), as_of)
        for account in accounts
    ]


def rank(scores: Iterable[AccountScore], top_n: int | None = None) -> list[AccountScore]:
    """Rank by score, then raw points, then account_id (stable, deterministic)."""
    ordered = sorted(
        scores, key=lambda s: (-s.score, -s.raw_points, s.account_id)
    )
    return ordered[:top_n] if top_n is not None else ordered
