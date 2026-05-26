"""Unit tests for the /api/stats Vercel serverless function (Tier A).

Covers:
- happy path: scoring artifact present, response matches the Tier-A contract
- degraded path: artifact missing, contract still satisfied, status="degraded"
- safety caps: oversize metric values are clamped
- uptime: trailing-30-day scheduled-run success rate
- never returns 5xx (handler always emits HTTP 200)
- the committed artifact is servable end-to-end
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add repo root/api to sys.path so we can import the api/stats.py module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
import stats  # type: ignore  # noqa: E402

NOW = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)


def _artifact(**overrides: object) -> dict:
    base = {
        "system": "revenue-signal-copilot",
        "mode": "live",
        "status": "operational",
        "generated_at": "2026-05-26T06:00:00Z",
        "metrics": {
            "accounts_total": 200,
            "accounts_scored_24h": 200,
            "signals_detected_24h": 7,
            "high_priority_accounts": 44,
        },
    }
    base.update(overrides)
    return base


def _history(run_count: int = 1, *, end: datetime = NOW) -> dict:
    runs = []
    for offset in range(run_count):
        ts = (end - timedelta(days=run_count - 1 - offset)).strftime("%Y-%m-%dT%H:%M:%SZ")
        runs.append({"run_id": f"rsc-{offset}", "generated_at": ts, "as_of": ts})
    return {"system": "revenue-signal-copilot", "schema_version": 1, "runs": runs}


class TierAResponseTests(unittest.TestCase):
    def test_happy_path_matches_contract(self) -> None:
        with patch.object(stats, "_load_scoring", return_value=_artifact()), \
                patch.object(stats, "_load_history", return_value=_history(1)):
            response = stats._build_response()

        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["status"], "operational")
        self.assertEqual(response["system"], stats.SYSTEM_SLUG)
        self.assertEqual(response["metrics"]["accounts_total"], 200)
        self.assertEqual(response["metrics"]["high_priority_accounts"], 44)
        self.assertEqual(set(response["metrics"]), set(stats.TIER_A_METRIC_KEYS))
        self.assertEqual(response["last_active_at"], "2026-05-26T06:00:00Z")
        self.assertIsInstance(response["uptime_pct_30d"], float)
        self.assertTrue(response["generated_at"].endswith("Z"))

    def test_degraded_when_artifact_missing(self) -> None:
        with patch.object(stats, "_load_scoring", return_value=None), \
                patch.object(stats, "_load_history", return_value=None):
            response = stats._build_response()

        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["status"], "degraded")
        self.assertEqual(response["metrics"]["accounts_total"], 0)
        self.assertEqual(response["metrics"]["high_priority_accounts"], 0)
        self.assertIsNone(response["last_active_at"])

    def test_metric_only_exposes_tier_a_keys(self) -> None:
        noisy = _artifact(metrics={
            "accounts_total": 200, "accounts_scored_24h": 200,
            "signals_detected_24h": 7, "high_priority_accounts": 44,
            "secret_internal_field": 999999,
        })
        with patch.object(stats, "_load_scoring", return_value=noisy), \
                patch.object(stats, "_load_history", return_value=_history(1)):
            response = stats._build_response()
        self.assertNotIn("secret_internal_field", response["metrics"])


class SafetyCapTests(unittest.TestCase):
    def test_oversize_values_are_clamped(self) -> None:
        self.assertEqual(stats._cap("accounts_total", 99_999_999_999), 10_000_000)
        self.assertEqual(stats._cap("high_priority_accounts", 50_000_000), 1_000_000)
        self.assertEqual(stats._cap("not_a_field", 42), 42)

    def test_runaway_metric_is_capped_in_response(self) -> None:
        wild = _artifact(metrics={
            "accounts_total": 10**12, "accounts_scored_24h": 10**9,
            "signals_detected_24h": 7, "high_priority_accounts": 44,
        })
        with patch.object(stats, "_load_scoring", return_value=wild), \
                patch.object(stats, "_load_history", return_value=_history(1)):
            response = stats._build_response()
        self.assertEqual(response["metrics"]["accounts_total"], 10_000_000)


class UptimeTests(unittest.TestCase):
    def test_empty_history_is_zero(self) -> None:
        self.assertEqual(stats._uptime_pct_30d({"runs": []}, NOW), 0.0)
        self.assertEqual(stats._uptime_pct_30d(None, NOW), 0.0)

    def test_single_recent_run_is_full(self) -> None:
        self.assertEqual(stats._uptime_pct_30d(_history(1), NOW), 100.0)

    def test_daily_runs_stay_high(self) -> None:
        uptime = stats._uptime_pct_30d(_history(30), NOW)
        self.assertGreaterEqual(uptime, 99.0)
        self.assertLessEqual(uptime, 100.0)

    def test_bounded_0_to_100(self) -> None:
        uptime = stats._uptime_pct_30d(_history(60), NOW)  # more runs than window
        self.assertLessEqual(uptime, 100.0)


class HandlerTests(unittest.TestCase):
    """Exercise the BaseHTTPRequestHandler entrypoint end-to-end."""

    def _invoke(self, method: str = "GET", *, scoring=None) -> tuple[int, dict, bytes]:
        rfile = io.BytesIO(f"{method} /api/stats HTTP/1.0\r\nHost: x\r\n\r\n".encode())
        wfile = io.BytesIO()
        h = stats.handler.__new__(stats.handler)
        h.rfile = rfile
        h.wfile = wfile
        h.client_address = ("127.0.0.1", 0)
        h.server = MagicMock()
        h.command = method
        h.path = "/api/stats"
        h.request_version = "HTTP/1.0"
        h.headers = {}
        h.requestline = f"{method} /api/stats HTTP/1.0"

        if method == "OPTIONS":
            h.do_OPTIONS()
        else:
            with patch.object(stats, "_load_scoring", return_value=scoring), \
                    patch.object(stats, "_load_history", return_value=None):
                h.do_GET()

        raw = wfile.getvalue().decode("utf-8", errors="replace")
        head, _, body = raw.partition("\r\n\r\n")
        status_code = int(head.split("\r\n", 1)[0].split(" ", 2)[1])
        hdrs = {}
        for line in head.split("\r\n")[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                hdrs[key] = value
        return status_code, hdrs, body.encode("utf-8")

    def test_get_returns_200_even_when_artifact_missing(self) -> None:
        status, hdrs, body = self._invoke("GET", scoring=None)
        self.assertEqual(status, 200)
        self.assertEqual(hdrs.get("Content-Type"), "application/json")
        self.assertEqual(hdrs.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("max-age=30", hdrs.get("Cache-Control", ""))
        payload = json.loads(body)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["mode"], "live")

    def test_get_serves_artifact_metrics(self) -> None:
        status, _, body = self._invoke("GET", scoring=_artifact())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["metrics"]["accounts_total"], 200)

    def test_options_returns_204(self) -> None:
        status, hdrs, _ = self._invoke("OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(hdrs.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(hdrs.get("Access-Control-Allow-Methods"), "GET, OPTIONS")


class CommittedArtifactTests(unittest.TestCase):
    """The seeded artifact on disk must actually serve as Tier-A operational."""

    def test_committed_artifact_is_operational(self) -> None:
        response = stats._build_response()
        self.assertEqual(response["status"], "operational")
        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["metrics"]["accounts_total"], 200)
        self.assertTrue(0 <= response["uptime_pct_30d"] <= 100)


if __name__ == "__main__":
    unittest.main()
