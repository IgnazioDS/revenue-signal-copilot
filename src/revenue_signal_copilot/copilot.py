from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class SignalDefinition:
    kind: str
    label: str
    base_weight: float
    half_life_days: int
    sentiment: str
    default_summary: str
    outreach_angle: str


@dataclass(frozen=True)
class RevenueSignal:
    account_id: str
    account_name: str
    signal_kind: str
    source: str
    captured_at: date
    strength: float
    summary: str


@dataclass(frozen=True)
class ScoredSignal:
    signal: RevenueSignal
    definition: SignalDefinition
    age_days: int
    decay_multiplier: float
    effective_points: float
    rationale: str


@dataclass(frozen=True)
class AccountScorecard:
    account_id: str
    account_name: str
    score: int
    total_points: float
    positive_points: float
    negative_points: float
    scored_signals: list[ScoredSignal]


SIGNAL_DEFINITIONS: dict[str, SignalDefinition] = {
    "job_change": SignalDefinition(
        kind="job_change",
        label="Executive job change",
        base_weight=22.0,
        half_life_days=45,
        sentiment="positive",
        default_summary="A decision-maker recently changed roles.",
        outreach_angle="Anchor outreach around a new leader's first-quarter priorities and change window.",
    ),
    "hiring_plan": SignalDefinition(
        kind="hiring_plan",
        label="Hiring plan",
        base_weight=16.0,
        half_life_days=60,
        sentiment="positive",
        default_summary="The account is actively hiring into a relevant function.",
        outreach_angle="Connect the pitch to team growth, operational load, and process scale.",
    ),
    "tech_stack_change": SignalDefinition(
        kind="tech_stack_change",
        label="Tech stack change",
        base_weight=18.0,
        half_life_days=50,
        sentiment="positive",
        default_summary="The account appears to be changing or expanding its tooling.",
        outreach_angle="Position against migration friction, integration risk, or workflow consolidation.",
    ),
    "website_engagement": SignalDefinition(
        kind="website_engagement",
        label="Website engagement",
        base_weight=10.0,
        half_life_days=21,
        sentiment="positive",
        default_summary="The account has shown recent website or content engagement.",
        outreach_angle="Follow up quickly while the account's research behavior is still fresh.",
    ),
    "rep_note": SignalDefinition(
        kind="rep_note",
        label="Rep note",
        base_weight=14.0,
        half_life_days=30,
        sentiment="positive",
        default_summary="A rep or operator recorded a concrete account insight.",
        outreach_angle="Use the internal observation directly in the opener instead of generic personalization.",
    ),
    "stakeholder_reply": SignalDefinition(
        kind="stakeholder_reply",
        label="Stakeholder reply",
        base_weight=20.0,
        half_life_days=14,
        sentiment="positive",
        default_summary="A stakeholder recently replied or re-engaged.",
        outreach_angle="Continue the thread while the conversation is active rather than restarting cold.",
    ),
    "funding_event": SignalDefinition(
        kind="funding_event",
        label="Funding event",
        base_weight=15.0,
        half_life_days=90,
        sentiment="positive",
        default_summary="The account recently raised capital or announced a financing event.",
        outreach_angle="Tie the message to deployment urgency and post-funding execution pressure.",
    ),
    "negative_note": SignalDefinition(
        kind="negative_note",
        label="Negative rep note",
        base_weight=18.0,
        half_life_days=45,
        sentiment="negative",
        default_summary="An internal note indicates low intent or a concrete blocker.",
        outreach_angle="Do not force outreach; resolve the blocker or deprioritize.",
    ),
    "stalled_opportunity": SignalDefinition(
        kind="stalled_opportunity",
        label="Stalled opportunity",
        base_weight=20.0,
        half_life_days=60,
        sentiment="negative",
        default_summary="An opportunity stalled or lost momentum.",
        outreach_angle="Treat as a rescue or requalification motion, not a standard push.",
    ),
}


def supported_signal_kinds() -> list[SignalDefinition]:
    return list(SIGNAL_DEFINITIONS.values())


def load_signals_from_csv(csv_path: str | Path) -> list[RevenueSignal]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {
            "account_id",
            "account_name",
            "signal_kind",
            "source",
            "captured_at",
            "strength",
            "summary",
        }
        missing = expected.difference(reader.fieldnames or [])
        if missing:
            joined = ", ".join(sorted(missing))
            raise ValueError(f"CSV is missing required columns: {joined}")

        signals: list[RevenueSignal] = []
        for row_number, row in enumerate(reader, start=2):
            kind = (row.get("signal_kind") or "").strip()
            if kind not in SIGNAL_DEFINITIONS:
                raise ValueError(
                    f"Unsupported signal_kind '{kind}' on row {row_number}. "
                    f"Run `revenue-signal-copilot signal-schema` for supported kinds."
                )

            account_id = (row.get("account_id") or "").strip()
            account_name = (row.get("account_name") or "").strip()
            source = (row.get("source") or "").strip()
            captured_at = _parse_date((row.get("captured_at") or "").strip(), row_number)
            strength = _parse_strength((row.get("strength") or "1.0").strip(), row_number)
            definition = SIGNAL_DEFINITIONS[kind]
            summary = (row.get("summary") or "").strip() or definition.default_summary

            if not account_id or not account_name or not source:
                raise ValueError(
                    f"Rows must include non-empty account_id, account_name, and source. "
                    f"Invalid row: {row_number}"
                )

            signals.append(
                RevenueSignal(
                    account_id=account_id,
                    account_name=account_name,
                    signal_kind=kind,
                    source=source,
                    captured_at=captured_at,
                    strength=strength,
                    summary=summary,
                )
            )

    return signals


def score_accounts(
    signals: list[RevenueSignal], as_of: date | None = None
) -> list[AccountScorecard]:
    effective_as_of = as_of or date.today()
    grouped: dict[tuple[str, str], list[RevenueSignal]] = {}

    for signal in signals:
        grouped.setdefault((signal.account_id, signal.account_name), []).append(signal)

    scorecards: list[AccountScorecard] = []
    for (account_id, account_name), account_signals in grouped.items():
        scored_signals = [
            _score_signal(signal, effective_as_of) for signal in account_signals
        ]
        scored_signals.sort(
            key=lambda item: abs(item.effective_points),
            reverse=True,
        )

        total_points = sum(item.effective_points for item in scored_signals)
        positive_points = sum(
            item.effective_points for item in scored_signals if item.effective_points > 0
        )
        negative_points = sum(
            abs(item.effective_points) for item in scored_signals if item.effective_points < 0
        )

        scorecards.append(
            AccountScorecard(
                account_id=account_id,
                account_name=account_name,
                score=_bounded_score(total_points),
                total_points=round(total_points, 2),
                positive_points=round(positive_points, 2),
                negative_points=round(negative_points, 2),
                scored_signals=scored_signals,
            )
        )

    scorecards.sort(key=lambda item: item.score, reverse=True)
    return scorecards


def build_account_brief(scorecard: AccountScorecard) -> str:
    positives = [item for item in scorecard.scored_signals if item.effective_points > 0][:3]
    negatives = [item for item in scorecard.scored_signals if item.effective_points < 0][:2]

    top_signal = positives[0] if positives else None
    urgency = _urgency_label(scorecard.score)
    risk_line = (
        "No material negative signal is currently suppressing the account."
        if not negatives
        else "; ".join(
            f"{item.definition.label} ({abs(item.effective_points):.1f} pts drag): {item.signal.summary}"
            for item in negatives
        )
    )
    outreach_angle = (
        top_signal.definition.outreach_angle
        if top_signal is not None
        else "Lead with discovery to validate whether there is any active buying motion."
    )

    lines = [
        f"Account Brief: {scorecard.account_name} ({scorecard.account_id})",
        "",
        f"Priority score: {scorecard.score}/100 ({urgency})",
        (
            f"Trace summary: {scorecard.positive_points:.1f} positive points minus "
            f"{scorecard.negative_points:.1f} negative points = {scorecard.total_points:.1f} net."
        ),
        "",
        "Why this account now:",
    ]

    if positives:
        lines.extend(
            f"- {item.definition.label}: {item.signal.summary} "
            f"[{item.effective_points:.1f} pts, {item.age_days}d old]"
            for item in positives
        )
    else:
        lines.append("- No active positive signal is strong enough to justify prioritization yet.")

    lines.extend(
        [
            "",
            "Risk / drag:",
            f"- {risk_line}",
            "",
            "Suggested outreach angle:",
            f"- {outreach_angle}",
            "",
            "Recommended next step:",
            f"- {_recommended_next_step(scorecard.score, bool(negatives))}",
        ]
    )
    return "\n".join(lines)


def format_scorecards(scorecards: list[AccountScorecard]) -> str:
    lines = ["Revenue Signal Scores", ""]
    for item in scorecards:
        lines.extend(
            [
                f"{item.account_name} ({item.account_id})",
                (
                    f"  Score: {item.score}/100 | Net: {item.total_points:.1f} pts | "
                    f"Positive: {item.positive_points:.1f} | Negative: {item.negative_points:.1f}"
                ),
                "  Top trace:",
            ]
        )
        for scored in item.scored_signals[:3]:
            sign = "+" if scored.effective_points >= 0 else "-"
            lines.append(
                f"  - {sign}{abs(scored.effective_points):.1f} {scored.definition.label} "
                f"from {scored.signal.source} ({scored.age_days}d): {scored.signal.summary}"
            )
        lines.append("")
    return "\n".join(lines).strip()


def format_signal_schema() -> str:
    lines = [
        "Supported revenue signals",
        "",
        "CSV columns:",
        "- account_id",
        "- account_name",
        "- signal_kind",
        "- source",
        "- captured_at  (YYYY-MM-DD)",
        "- strength     (0.0 to 1.5, default 1.0)",
        "- summary      (optional; falls back to a default summary)",
        "",
        "Signal kinds:",
    ]
    for definition in supported_signal_kinds():
        lines.append(
            (
                f"- {definition.kind}: {definition.label} | "
                f"base_weight={definition.base_weight:.0f} | "
                f"half_life_days={definition.half_life_days} | "
                f"sentiment={definition.sentiment}"
            )
        )
    return "\n".join(lines)


def scorecards_to_dict(scorecards: list[AccountScorecard]) -> list[dict[str, object]]:
    return [
        {
            "account_id": item.account_id,
            "account_name": item.account_name,
            "score": item.score,
            "total_points": item.total_points,
            "positive_points": item.positive_points,
            "negative_points": item.negative_points,
            "signals": [
                {
                    "signal_kind": scored.signal.signal_kind,
                    "label": scored.definition.label,
                    "source": scored.signal.source,
                    "captured_at": scored.signal.captured_at.isoformat(),
                    "strength": scored.signal.strength,
                    "summary": scored.signal.summary,
                    "age_days": scored.age_days,
                    "decay_multiplier": scored.decay_multiplier,
                    "effective_points": scored.effective_points,
                    "sentiment": scored.definition.sentiment,
                    "rationale": scored.rationale,
                }
                for scored in item.scored_signals
            ],
        }
        for item in scorecards
    ]


def signal_schema_to_dict() -> dict[str, object]:
    return {
        "required_columns": [
            "account_id",
            "account_name",
            "signal_kind",
            "source",
            "captured_at",
            "strength",
            "summary",
        ],
        "signal_kinds": [
            {
                "kind": definition.kind,
                "label": definition.label,
                "base_weight": definition.base_weight,
                "half_life_days": definition.half_life_days,
                "sentiment": definition.sentiment,
                "default_summary": definition.default_summary,
                "outreach_angle": definition.outreach_angle,
            }
            for definition in supported_signal_kinds()
        ],
    }


def _score_signal(signal: RevenueSignal, as_of: date) -> ScoredSignal:
    definition = SIGNAL_DEFINITIONS[signal.signal_kind]
    age_days = max((as_of - signal.captured_at).days, 0)
    decay_multiplier = 0.5 ** (age_days / definition.half_life_days)
    signed_weight = definition.base_weight if definition.sentiment == "positive" else -definition.base_weight
    effective_points = signed_weight * signal.strength * decay_multiplier
    rationale = (
        f"{definition.label} from {signal.source} contributes {effective_points:.1f} points "
        f"after {age_days} days of decay."
    )
    return ScoredSignal(
        signal=signal,
        definition=definition,
        age_days=age_days,
        decay_multiplier=round(decay_multiplier, 4),
        effective_points=round(effective_points, 2),
        rationale=rationale,
    )


def _bounded_score(total_points: float) -> int:
    return max(0, min(100, int(round(total_points))))


def _parse_date(value: str, row_number: int) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"captured_at must be YYYY-MM-DD on row {row_number}; got '{value}'"
        ) from exc


def _parse_strength(value: str, row_number: int) -> float:
    try:
        strength = float(value)
    except ValueError as exc:
        raise ValueError(f"strength must be numeric on row {row_number}; got '{value}'") from exc

    if strength < 0 or strength > 1.5:
        raise ValueError(
            f"strength must be between 0.0 and 1.5 on row {row_number}; got {strength}"
        )
    return strength


def _urgency_label(score: int) -> str:
    if score >= 70:
        return "high urgency"
    if score >= 45:
        return "worth active pursuit"
    if score >= 25:
        return "monitor"
    return "low priority"


def _recommended_next_step(score: int, has_negative_signal: bool) -> str:
    if score >= 70:
        return "Route to an AE now with a tailored opener grounded in the top two signals."
    if score >= 45:
        return "Run a focused outbound sequence tied to the strongest current signal."
    if has_negative_signal:
        return "Requalify before pushing outreach; the downside signal is still material."
    return "Keep monitoring for fresher intent before spending seller time."
