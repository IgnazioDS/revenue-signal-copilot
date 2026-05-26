"""Tests for the committed public fixture and its loaders.

These assert the on-disk contract the scoring runner depends on: the files load,
parse into typed domain objects, reference only known accounts and signal kinds,
and score end-to-end without error.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from revenue_signal_copilot import fixtures, scoring

REFERENCE = datetime(2026, 5, 26, tzinfo=timezone.utc)


class ParseIsoTests(unittest.TestCase):
    def test_z_suffix_becomes_aware_utc(self) -> None:
        parsed = fixtures.parse_iso("2026-05-20T14:31:00Z")
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset(), timezone.utc.utcoffset(parsed))

    def test_naive_assumed_utc(self) -> None:
        parsed = fixtures.parse_iso("2026-05-20T14:31:00")
        self.assertIsNotNone(parsed.tzinfo)


class AccountFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = fixtures.load_accounts()

    def test_count_and_unique_ids(self) -> None:
        self.assertEqual(len(self.accounts), 200)
        ids = [a.account_id for a in self.accounts]
        self.assertEqual(len(set(ids)), len(ids))

    def test_fields_well_formed(self) -> None:
        for account in self.accounts:
            self.assertIsInstance(account.employee_count, int)
            self.assertIn(account.region, {"NA", "EMEA", "APAC", "LATAM"})
            self.assertTrue(account.name)


class SignalFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = fixtures.load_accounts()
        self.signals = fixtures.load_signals()

    def test_count_in_expected_range(self) -> None:
        self.assertGreaterEqual(len(self.signals), 800)
        self.assertLessEqual(len(self.signals), 1300)

    def test_all_kinds_known(self) -> None:
        for signal in self.signals:
            self.assertIn(signal.kind, scoring.SIGNAL_KINDS)

    def test_all_signals_reference_known_accounts(self) -> None:
        known = {a.account_id for a in self.accounts}
        for signal in self.signals:
            self.assertIn(signal.account_id, known)

    def test_captured_at_is_aware_and_not_future(self) -> None:
        for signal in self.signals:
            self.assertIsNotNone(signal.captured_at.tzinfo)
            self.assertLessEqual(signal.captured_at, REFERENCE)

    def test_all_four_kinds_present(self) -> None:
        kinds = {s.kind for s in self.signals}
        self.assertEqual(kinds, set(scoring.SIGNAL_KINDS))


class OutcomeFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = fixtures.load_accounts()
        self.outcomes = fixtures.load_outcomes()

    def test_count_and_values(self) -> None:
        self.assertEqual(len(self.outcomes), 50)
        self.assertTrue(set(self.outcomes.values()) <= {"won", "lost"})

    def test_both_classes_present(self) -> None:
        self.assertIn("won", self.outcomes.values())
        self.assertIn("lost", self.outcomes.values())

    def test_labels_reference_known_accounts(self) -> None:
        known = {a.account_id for a in self.accounts}
        for account_id in self.outcomes:
            self.assertIn(account_id, known)


class FixtureScoringIntegrationTests(unittest.TestCase):
    def test_scores_end_to_end(self) -> None:
        accounts = fixtures.load_accounts()
        signals = fixtures.load_signals()
        scores = scoring.score_accounts(accounts, signals, REFERENCE)
        self.assertEqual(len(scores), 200)
        self.assertTrue(all(0 <= s.score <= 100 for s in scores))
        # The fixture is designed to yield a meaningful high-priority cohort.
        self.assertGreater(sum(1 for s in scores if s.priority == "high"), 5)


if __name__ == "__main__":
    unittest.main()
