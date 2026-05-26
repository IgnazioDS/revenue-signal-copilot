"""Unit tests for the explainable scoring engine (revenue_signal_copilot.scoring).

The engine encodes the product thesis as testable properties:
- Scoring is additive: the trace points sum to the (pre-cap) raw score, so a
  rep can defend the number factor by factor.
- Recency is exponential decay per signal kind, so a fresh weak signal can and
  must outweigh a stale strong one ("recency dominance").
- No black-box: same inputs always produce an identical, frozen result.
"""
from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timedelta, timezone

from revenue_signal_copilot import scoring


def _utc(days_ago: float, *, now: datetime) -> datetime:
    return now - timedelta(days=days_ago)


NOW = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)


def _sig(account_id: str, kind: str, days_ago: float, *, seniority: str | None = None,
         signal_id: str = "s", source: str = "test") -> scoring.Signal:
    return scoring.Signal(
        signal_id=signal_id,
        account_id=account_id,
        kind=kind,
        source=source,
        captured_at=_utc(days_ago, now=NOW),
        seniority=seniority,
    )


def _acct(account_id: str = "a1", name: str = "Northwind Logistics") -> scoring.Account:
    return scoring.Account(
        account_id=account_id, name=name, industry="Logistics",
        employee_count=500, region="NA",
    )


class RecencyDecayTests(unittest.TestCase):
    def test_factor_is_one_at_age_zero(self) -> None:
        self.assertEqual(scoring.recency_factor(0.0, 45.0), 1.0)

    def test_negative_age_treated_as_fresh(self) -> None:
        self.assertEqual(scoring.recency_factor(-3.0, 45.0), 1.0)

    def test_factor_is_half_at_one_half_life(self) -> None:
        self.assertAlmostEqual(scoring.recency_factor(45.0, 45.0), 0.5, places=9)

    def test_factor_is_quarter_at_two_half_lives(self) -> None:
        self.assertAlmostEqual(scoring.recency_factor(90.0, 45.0), 0.25, places=9)

    def test_monotonic_decreasing(self) -> None:
        prev = 1.01
        for age in range(0, 400, 7):
            cur = scoring.recency_factor(float(age), 30.0)
            self.assertLessEqual(cur, prev)
            prev = cur

    def test_nonpositive_half_life_rejected(self) -> None:
        with self.assertRaises(ValueError):
            scoring.recency_factor(10.0, 0.0)


class ScoreAccountTests(unittest.TestCase):
    def test_trace_sorted_by_points_desc(self) -> None:
        sigs = [
            _sig("a1", "hiring", 60, signal_id="weak"),
            _sig("a1", "job_change", 5, seniority="VP+", signal_id="strong"),
        ]
        result = scoring.score_account(_acct(), sigs, NOW)
        points = [e.points for e in result.trace]
        self.assertEqual(points, sorted(points, reverse=True))
        self.assertEqual(result.trace[0].signal_id, "strong")

    def test_trace_points_sum_to_raw(self) -> None:
        sigs = [
            _sig("a1", "job_change", 5, seniority="VP+"),
            _sig("a1", "infra_shift", 10),
            _sig("a1", "internal_note", 90),
        ]
        result = scoring.score_account(_acct(), sigs, NOW)
        self.assertAlmostEqual(
            sum(e.points for e in result.trace), result.raw_points, places=2
        )

    def test_score_matches_priority_transform(self) -> None:
        sigs = [
            _sig("a1", "job_change", 2, seniority="VP+"),
            _sig("a1", "infra_shift", 6),
            _sig("a1", "internal_note", 30),
        ]
        result = scoring.score_account(_acct(), sigs, NOW)
        self.assertEqual(result.score, scoring.priority_score(result.raw_points))
        self.assertLessEqual(result.score, 100)

    def test_overwhelming_signals_cap_at_100(self) -> None:
        sigs = [_sig("a1", "job_change", 0, seniority="VP+", signal_id=f"s{i}")
                for i in range(10)]
        result = scoring.score_account(_acct(), sigs, NOW)
        self.assertEqual(result.score, 100)

    def test_seniority_bonus_increases_score(self) -> None:
        plain = scoring.score_account(_acct(), [_sig("a1", "job_change", 5)], NOW)
        senior = scoring.score_account(
            _acct(), [_sig("a1", "job_change", 5, seniority="VP+")], NOW
        )
        self.assertGreater(senior.raw_points, plain.raw_points)

    def test_ignores_signals_for_other_accounts(self) -> None:
        sigs = [_sig("OTHER", "job_change", 1, seniority="VP+")]
        result = scoring.score_account(_acct("a1"), sigs, NOW)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.trace, ())

    def test_unknown_kind_rejected(self) -> None:
        bad = scoring.Signal("s", "a1", "telepathy", "test", NOW)
        with self.assertRaises(ValueError):
            scoring.score_account(_acct(), [bad], NOW)

    def test_empty_signals_scores_zero(self) -> None:
        result = scoring.score_account(_acct(), [], NOW)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.priority, "low")
        self.assertIn("no active signals", result.why.lower())


class PriorityScoreTransformTests(unittest.TestCase):
    """The evidence-points -> 0-100 mapping: identity below the knee, then
    diminishing-returns compression toward 100."""

    def test_identity_below_knee(self) -> None:
        for raw in (0.0, 10.0, 35.0, scoring.KNEE_RAW):
            self.assertEqual(scoring.priority_score(raw), round(raw))

    def test_compresses_above_knee(self) -> None:
        score = scoring.priority_score(100.0)
        self.assertGreater(score, scoring.KNEE_RAW)  # still high
        self.assertLess(score, 100)  # not pinned at the ceiling
        self.assertLess(score, round(100.0))  # compressed below the raw total

    def test_monotonic_increasing(self) -> None:
        prev = -1
        for raw in range(0, 600, 5):
            cur = scoring.priority_score(float(raw))
            self.assertGreaterEqual(cur, prev)
            prev = cur

    def test_bounded_0_to_100(self) -> None:
        self.assertEqual(scoring.priority_score(0.0), 0)
        self.assertGreaterEqual(scoring.priority_score(-5.0), 0)
        self.assertLessEqual(scoring.priority_score(10_000.0), 100)

    def test_differentiates_signal_rich_accounts(self) -> None:
        # The whole point of the knee: two over-the-knee accounts with different
        # evidence totals get different scores instead of both pinning at 100.
        self.assertNotEqual(
            scoring.priority_score(110.0), scoring.priority_score(160.0)
        )


class RecencyDominanceTests(unittest.TestCase):
    """The central thesis: time-weighting beats raw signal quality."""

    def test_fresh_signal_beats_stale_same_kind(self) -> None:
        fresh = scoring.score_account(_acct(), [_sig("a1", "job_change", 7)], NOW)
        stale = scoring.score_account(_acct(), [_sig("a1", "job_change", 540)], NOW)
        self.assertGreater(fresh.score, stale.score)

    def test_fresh_weak_signal_beats_stale_strong_signal(self) -> None:
        # README claim: a 7-day hiring post (low base) outscores an 18-month
        # job-change (high base). Un-weighted "quality" loses to recency.
        fresh_weak = scoring.score_account(_acct(), [_sig("a1", "hiring", 7)], NOW)
        stale_strong = scoring.score_account(
            _acct(), [_sig("a1", "job_change", 540, seniority="VP+")], NOW
        )
        self.assertGreater(fresh_weak.score, stale_strong.score)


class PriorityTests(unittest.TestCase):
    def test_priority_bands(self) -> None:
        self.assertEqual(scoring.priority_for(85), "high")
        self.assertEqual(scoring.priority_for(scoring.HIGH_PRIORITY_THRESHOLD), "high")
        self.assertEqual(scoring.priority_for(scoring.WATCH_THRESHOLD), "watch")
        self.assertEqual(scoring.priority_for(scoring.WATCH_THRESHOLD - 1), "low")
        self.assertEqual(scoring.priority_for(0), "low")

    def test_high_priority_account_end_to_end(self) -> None:
        sigs = [
            _sig("a1", "job_change", 5, seniority="VP+"),
            _sig("a1", "infra_shift", 10),
        ]
        result = scoring.score_account(_acct(), sigs, NOW)
        self.assertGreaterEqual(result.score, scoring.HIGH_PRIORITY_THRESHOLD)
        self.assertEqual(result.priority, "high")


class WhySentenceTests(unittest.TestCase):
    def test_why_names_account_score_and_top_factor(self) -> None:
        result = scoring.score_account(_acct(), [_sig("a1", "job_change", 5)], NOW)
        self.assertIn("Northwind Logistics", result.why)
        self.assertIn(str(result.score), result.why)
        self.assertIn("job-change", result.why)

    def test_why_contains_no_em_dash(self) -> None:
        sigs = [_sig("a1", "job_change", 5), _sig("a1", "hiring", 12)]
        result = scoring.score_account(_acct(), sigs, NOW)
        self.assertNotIn("—", result.why)


class BatchAndRankTests(unittest.TestCase):
    def _accounts(self) -> list[scoring.Account]:
        return [_acct(f"a{i}", f"Account {i}") for i in range(5)]

    def test_score_accounts_returns_one_per_account(self) -> None:
        accts = self._accounts()
        sigs = [_sig("a0", "job_change", 3), _sig("a2", "hiring", 1)]
        scores = scoring.score_accounts(accts, sigs, NOW)
        self.assertEqual(len(scores), len(accts))

    def test_rank_orders_by_score_then_top_n(self) -> None:
        accts = self._accounts()
        sigs = [
            _sig("a3", "job_change", 2, seniority="VP+"),
            _sig("a1", "hiring", 1),
        ]
        scores = scoring.score_accounts(accts, sigs, NOW)
        ranked = scoring.rank(scores, top_n=3)
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0].account_id, "a3")
        self.assertGreaterEqual(ranked[0].score, ranked[1].score)

    def test_deterministic(self) -> None:
        accts = self._accounts()
        sigs = [_sig("a0", "job_change", 3), _sig("a2", "hiring", 1)]
        first = scoring.score_accounts(accts, sigs, NOW)
        second = scoring.score_accounts(accts, sigs, NOW)
        self.assertEqual(first, second)


class ImmutabilityTests(unittest.TestCase):
    def test_account_score_is_frozen(self) -> None:
        result = scoring.score_account(_acct(), [_sig("a1", "job_change", 5)], NOW)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.score = 0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
