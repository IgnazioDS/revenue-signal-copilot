from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .catalog import load_project
from .copilot import (
    build_account_brief,
    format_scorecards,
    format_signal_schema,
    load_signals_from_csv,
    score_accounts,
    scorecards_to_dict,
    signal_schema_to_dict,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="revenue-signal-copilot", description="Operate Revenue Signal Copilot.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("summary", help="Print product summary.")
    subparsers.add_parser("capabilities", help="Print initial capabilities.")
    subparsers.add_parser("roadmap", help="Print roadmap.")
    schema_parser = subparsers.add_parser(
        "signal-schema", help="Print the supported CSV schema and signal kinds."
    )
    schema_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )

    score_parser = subparsers.add_parser("score-csv", help="Score accounts from a CSV signal export.")
    score_parser.add_argument("csv_path", help="Path to a CSV file of revenue signals.")
    score_parser.add_argument(
        "--as-of",
        dest="as_of",
        help="Score as of YYYY-MM-DD instead of today.",
    )
    score_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )

    brief_parser = subparsers.add_parser(
        "brief-account",
        help="Generate an account brief from the score trace.",
    )
    brief_parser.add_argument("csv_path", help="Path to a CSV file of revenue signals.")
    brief_parser.add_argument("--account-id", required=True, help="Account ID to brief.")
    brief_parser.add_argument(
        "--as-of",
        dest="as_of",
        help="Score as of YYYY-MM-DD instead of today.",
    )
    brief_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def run(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    project = load_project()

    if args.command == "summary":
        return "\n".join([
            project.name,
            "=" * len(project.name),
            project.summary,
            "",
            f"Problem: {project.problem}",
            f"Users: {project.users}",
            f"Stage: {project.stage}",
            f"Track: {project.track}",
        ])
    if args.command == "capabilities":
        lines = [project.name, "", "Core capabilities:"]
        lines.extend(f"- {item}" for item in project.mvp)
        return "\n".join(lines)
    if args.command == "roadmap":
        roadmap_path = Path(__file__).resolve().parents[2] / "docs" / "roadmap.md"
        return roadmap_path.read_text(encoding="utf-8").strip()
    if args.command == "signal-schema":
        if args.format == "json":
            return json.dumps(signal_schema_to_dict(), indent=2)
        return format_signal_schema()
    if args.command == "score-csv":
        signals = load_signals_from_csv(args.csv_path)
        scorecards = score_accounts(signals, as_of=_parse_as_of(args.as_of))
        if args.format == "json":
            return json.dumps(scorecards_to_dict(scorecards), indent=2)
        return format_scorecards(scorecards)
    if args.command == "brief-account":
        signals = load_signals_from_csv(args.csv_path)
        scorecards = score_accounts(signals, as_of=_parse_as_of(args.as_of))
        for scorecard in scorecards:
            if scorecard.account_id == args.account_id:
                if args.format == "json":
                    return json.dumps(
                        {
                            "account_id": scorecard.account_id,
                            "account_name": scorecard.account_name,
                            "score": scorecard.score,
                            "brief": build_account_brief(scorecard),
                            "trace": scorecards_to_dict([scorecard])[0]["signals"],
                        },
                        indent=2,
                    )
                return build_account_brief(scorecard)
        raise ValueError(f"Unknown account_id: {args.account_id}")
    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    print(run(argv))
    return 0


def _parse_as_of(value: str | None) -> datetime.date | None:
    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


if __name__ == "__main__":
    raise SystemExit(main())
