"""Tests for the benchmark runner that publishes the daily scoring artifact.

The runner is the "git-as-database" writer: it scores the fixture as of a run
date (plus a small date-seeded daily injection so the public benchmark moves),
then emits api/_scoring_latest.json and appends to api/_scoring_history.json.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from revenue_signal_copilot import fixtures, scoring, scoring_runner

DAY = datetime(2026, 5, 26, 6, 0, 0, tzinfo=timezone.utc)
NEXT_DAY = DAY + timedelta(days=1)


class DailyInjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = fixtures.load_accounts()

    def test_count_in_range_and_fresh(self) -> None:
        injected = scoring_runner.inject_daily_signals(DAY, self.accounts)
        self.assertGreaterEqual(len(injected), 1)
        self.assertLessEqual(len(injected), 3)
        for signal in injected:
            self.assertIn(signal.kind, scoring.SIGNAL_KINDS)
            self.assertLessEqual(signal.captured_at, DAY)
            self.assertGreaterEqual(signal.captured_at, DAY - timedelta(days=2))

    def test_deterministic_per_date(self) -> None:
        first = scoring_runner.inject_daily_signals(DAY, self.accounts)
        second = scoring_runner.inject_daily_signals(DAY, self.accounts)
        self.assertEqual([s.signal_id for s in first], [s.signal_id for s in second])
        self.assertEqual(
            [s.account_id for s in first], [s.account_id for s in second]
        )

    def test_varies_across_dates(self) -> None:
        today = scoring_runner.inject_daily_signals(DAY, self.accounts)
        tomorrow = scoring_runner.inject_daily_signals(NEXT_DAY, self.accounts)
        self.assertNotEqual(
            [s.signal_id for s in today], [s.signal_id for s in tomorrow]
        )

    def test_injected_signals_reference_known_accounts(self) -> None:
        known = {a.account_id for a in self.accounts}
        for signal in scoring_runner.inject_daily_signals(DAY, self.accounts):
            self.assertIn(signal.account_id, known)


class PrecisionAtKTests(unittest.TestCase):
    def test_perfect_when_top_all_won(self) -> None:
        ranked = [
            scoring.AccountScore("a1", "A1", "SaaS", 90, 90.0, "high", (), "", ()),
            scoring.AccountScore("a2", "A2", "SaaS", 80, 80.0, "high", (), "", ()),
        ]
        outcomes = {"a1": "won", "a2": "won"}
        self.assertEqual(scoring_runner.precision_at_k(ranked, outcomes, k=2), 1.0)

    def test_half_when_split(self) -> None:
        ranked = [
            scoring.AccountScore("a1", "A1", "SaaS", 90, 90.0, "high", (), "", ()),
            scoring.AccountScore("a2", "A2", "SaaS", 80, 80.0, "high", (), "", ()),
        ]
        outcomes = {"a1": "won", "a2": "lost"}
        self.assertEqual(scoring_runner.precision_at_k(ranked, outcomes, k=2), 0.5)

    def test_none_when_no_labeled_in_top(self) -> None:
        ranked = [scoring.AccountScore("a1", "A1", "SaaS", 90, 90.0, "high", (), "", ())]
        self.assertIsNone(scoring_runner.precision_at_k(ranked, {}, k=2))


class BuildArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = fixtures.load_accounts()
        self.signals = fixtures.load_signals()
        self.outcomes = fixtures.load_outcomes()
        self.artifact = scoring_runner.build_artifact(
            DAY, self.accounts, self.signals, self.outcomes, previous=None, top_n=20
        )

    def test_envelope(self) -> None:
        self.assertEqual(self.artifact["system"], "revenue-signal-copilot")
        self.assertEqual(self.artifact["mode"], "live")
        self.assertEqual(self.artifact["status"], "operational")
        self.assertEqual(self.artifact["schema_version"], 1)
        self.assertEqual(self.artifact["dataset_kind"], "synthetic-public")
        self.assertTrue(self.artifact["fixture"])
        self.assertTrue(self.artifact["generated_at"].endswith("Z"))
        self.assertTrue(self.artifact["run_id"])

    def test_metrics(self) -> None:
        metrics = self.artifact["metrics"]
        self.assertEqual(metrics["accounts_total"], 200)
        self.assertEqual(metrics["accounts_scored_24h"], 200)
        self.assertIsInstance(metrics["signals_detected_24h"], int)
        self.assertGreaterEqual(metrics["signals_detected_24h"], 1)  # injected at least
        self.assertEqual(
            metrics["high_priority_accounts"],
            sum(
                1
                for s in scoring.score_accounts(self.accounts, self.signals, DAY)
                if s.priority == "high"
            ),
        )

    def test_ranked_accounts_shape(self) -> None:
        ranked = self.artifact["ranked_accounts"]
        self.assertEqual(len(ranked), 20)
        scores = [r["score"] for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
        first = ranked[0]
        for key in ("rank", "account_id", "name", "score", "priority", "why", "trace",
                    "evidence_points", "top_kinds"):
            self.assertIn(key, first)
        self.assertEqual(first["rank"], 1)
        self.assertTrue(first["trace"])  # top account has signals
        for entry in first["trace"]:
            for key in ("kind", "source", "captured_at", "points", "reason"):
                self.assertIn(key, entry)

    def test_top_signals_breakdown(self) -> None:
        top = self.artifact["top_signals"]
        self.assertTrue(top)
        kinds = {row["kind"] for row in top}
        self.assertTrue(kinds <= set(scoring.SIGNAL_KINDS))
        self.assertTrue(all("count" in row and "share" in row for row in top))

    def test_calibration_present(self) -> None:
        cal = self.artifact["calibration"]
        self.assertEqual(cal["k"], 20)
        self.assertIn("precision", cal)
        self.assertIn("baseline_win_rate", cal)

    def test_previous_run_delta(self) -> None:
        previous = {
            "run_id": "rsc-prev",
            "generated_at": "2026-05-25T06:00:00Z",
            "metrics": {"high_priority_accounts": self.artifact["metrics"][
                "high_priority_accounts"] - 3},
            "top_account_id": "acct_9999",
            "top_account_name": "Old Leader",
        }
        artifact = scoring_runner.build_artifact(
            DAY, self.accounts, self.signals, self.outcomes, previous=previous, top_n=20
        )
        delta = artifact["previous_run"]["delta"]
        self.assertEqual(delta["high_priority_accounts"], 3)
        self.assertTrue(delta["top_account_changed"])

    def test_no_previous_run_is_null(self) -> None:
        self.assertIsNone(self.artifact["previous_run"])

    def test_deterministic_given_as_of(self) -> None:
        again = scoring_runner.build_artifact(
            DAY, self.accounts, self.signals, self.outcomes, previous=None, top_n=20
        )
        self.assertEqual(self.artifact, again)


class RunWritesArtifactTests(unittest.TestCase):
    def test_run_writes_latest_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            artifact = scoring_runner.run(as_of=DAY, out_dir=out)
            latest_path = out / scoring_runner.ARTIFACT_FILENAME
            history_path = out / scoring_runner.HISTORY_FILENAME
            self.assertTrue(latest_path.exists())
            self.assertTrue(history_path.exists())
            written = json.loads(latest_path.read_text())
            self.assertEqual(written["run_id"], artifact["run_id"])
            history = json.loads(history_path.read_text())
            self.assertEqual(len(history["runs"]), 1)
            self.assertEqual(history["runs"][-1]["run_id"], artifact["run_id"])

    def test_second_run_appends_and_sets_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            scoring_runner.run(as_of=DAY, out_dir=out)
            second = scoring_runner.run(as_of=NEXT_DAY, out_dir=out)
            history = json.loads((out / scoring_runner.HISTORY_FILENAME).read_text())
            self.assertEqual(len(history["runs"]), 2)
            self.assertIsNotNone(second["previous_run"])

    def test_history_trimmed_to_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            day = DAY
            for _ in range(scoring_runner.HISTORY_CAP + 5):
                scoring_runner.run(as_of=day, out_dir=out)
                day += timedelta(days=1)
            history = json.loads((out / scoring_runner.HISTORY_FILENAME).read_text())
            self.assertEqual(len(history["runs"]), scoring_runner.HISTORY_CAP)


if __name__ == "__main__":
    unittest.main()
