from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from revenue_signal_copilot.copilot import (
    build_account_brief,
    load_signals_from_csv,
    score_accounts,
)


class CopilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.example_csv = Path(__file__).resolve().parent.parent / "examples" / "revenue_signals.csv"

    def test_load_signals_from_csv(self) -> None:
        signals = load_signals_from_csv(self.example_csv)
        self.assertEqual(len(signals), 8)
        self.assertEqual(signals[0].account_id, "acct-001")
        self.assertEqual(signals[0].signal_kind, "job_change")

    def test_score_accounts_applies_recency_decay(self) -> None:
        signals = load_signals_from_csv(self.example_csv)
        scorecards = score_accounts(signals, as_of=date(2026, 5, 13))
        by_id = {item.account_id: item for item in scorecards}

        northstar = by_id["acct-001"]
        polar = by_id["acct-003"]
        acme = by_id["acct-002"]

        self.assertGreater(northstar.score, acme.score)
        self.assertGreater(polar.score, acme.score)
        self.assertGreater(northstar.positive_points, 0)
        self.assertGreater(acme.negative_points, 0)

    def test_build_account_brief_uses_trace(self) -> None:
        signals = load_signals_from_csv(self.example_csv)
        scorecard = score_accounts(signals, as_of=date(2026, 5, 13))[0]
        brief = build_account_brief(scorecard)

        self.assertIn(scorecard.account_name, brief)
        self.assertIn("Trace summary:", brief)
        self.assertIn("Recommended next step:", brief)


if __name__ == "__main__":
    unittest.main()
