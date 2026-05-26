from __future__ import annotations

import json
import unittest
from pathlib import Path

from revenue_signal_copilot.cli import run


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.example_csv = str(
            Path(__file__).resolve().parent.parent / "examples" / "revenue_signals.csv"
        )

    def test_summary(self) -> None:
        output = run(["summary"])
        self.assertIn("Revenue Signal Copilot", output)
        self.assertIn("Outbound teams chase low-signal leads because enrichment and prioritization are fragmented across tools.", output)

    def test_capabilities(self) -> None:
        output = run(["capabilities"])
        self.assertIn("Core capabilities:", output)
        self.assertIn("Ingest CRM exports and website data", output)

    def test_roadmap(self) -> None:
        output = run(["roadmap"])
        self.assertIn("# Roadmap", output)
        self.assertIn("## Phase 1", output)

    def test_signal_schema(self) -> None:
        output = run(["signal-schema"])
        self.assertIn("Supported revenue signals", output)
        self.assertIn("job_change", output)
        self.assertIn("stalled_opportunity", output)

    def test_signal_schema_json(self) -> None:
        output = run(["signal-schema", "--format", "json"])
        payload = json.loads(output)
        self.assertIn("required_columns", payload)
        self.assertIn("signal_kinds", payload)

    def test_score_csv(self) -> None:
        output = run(["score-csv", self.example_csv, "--as-of", "2026-05-13"])
        self.assertIn("Revenue Signal Scores", output)
        self.assertIn("Northstar Health", output)
        self.assertIn("Polar Cloud", output)

    def test_brief_account(self) -> None:
        output = run(
            [
                "brief-account",
                self.example_csv,
                "--account-id",
                "acct-003",
                "--as-of",
                "2026-05-13",
            ]
        )
        self.assertIn("Account Brief: Polar Cloud", output)
        self.assertIn("Priority score:", output)
        self.assertIn("Suggested outreach angle:", output)

    def test_score_csv_json(self) -> None:
        output = run(
            ["score-csv", self.example_csv, "--as-of", "2026-05-13", "--format", "json"]
        )
        payload = json.loads(output)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["account_id"], "acct-001")
        self.assertIn("signals", payload[0])

    def test_score_lists_top_accounts_with_traces(self) -> None:
        output = run(["score", "--top", "3"])
        self.assertIn("high-priority", output)
        # Each ranked account carries a defensible "why" line.
        self.assertEqual(output.count("/100 on"), 3)

    def test_score_default_reports_evidence(self) -> None:
        output = run(["score"])
        self.assertIn("evidence points", output)


if __name__ == "__main__":
    unittest.main()
