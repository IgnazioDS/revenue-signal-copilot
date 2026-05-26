"""Unit tests for the /api/scoring-latest Vercel serverless function.

The file is hyphenated (Vercel maps the filename to the route), so it is loaded
by path rather than imported by name.

Covers: serves the committed artifact, degrades gracefully when it is missing,
never returns 5xx, OPTIONS preflight, and CORS + cache headers.
"""
from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

API_DIR = Path(__file__).resolve().parent.parent / "api"


def _load_endpoint():
    spec = importlib.util.spec_from_file_location(
        "scoring_latest_endpoint", API_DIR / "scoring-latest.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


endpoint = _load_endpoint()


class BuildResponseTests(unittest.TestCase):
    def test_serves_committed_artifact(self) -> None:
        response = endpoint.build_response()
        self.assertEqual(response["system"], "revenue-signal-copilot")
        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["dataset_kind"], "synthetic-public")
        self.assertTrue(response["ranked_accounts"])  # seeded artifact has accounts
        self.assertEqual(response["ranked_accounts"][0]["rank"], 1)

    def test_degraded_payload_when_artifact_missing(self) -> None:
        with patch.object(endpoint, "_load_artifact", return_value=None):
            response = endpoint.build_response()
        self.assertEqual(response["status"], "degraded")
        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["dataset_kind"], "synthetic-public")
        self.assertEqual(response["ranked_accounts"], [])
        self.assertEqual(response["metrics"]["accounts_total"], 0)
        self.assertIsNone(response["previous_run"])


class HandlerTests(unittest.TestCase):
    def _invoke(self, method: str = "GET", *, artifact_missing: bool = False):
        rfile = io.BytesIO(
            f"{method} /api/scoring-latest HTTP/1.0\r\nHost: x\r\n\r\n".encode()
        )
        wfile = io.BytesIO()
        h = endpoint.handler.__new__(endpoint.handler)
        h.rfile = rfile
        h.wfile = wfile
        h.client_address = ("127.0.0.1", 0)
        h.server = MagicMock()
        h.command = method
        h.path = "/api/scoring-latest"
        h.request_version = "HTTP/1.0"
        h.headers = {}
        h.requestline = f"{method} /api/scoring-latest HTTP/1.0"

        if method == "OPTIONS":
            h.do_OPTIONS()
        elif artifact_missing:
            with patch.object(endpoint, "_load_artifact", return_value=None):
                h.do_GET()
        else:
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

    def test_get_returns_200_with_artifact(self) -> None:
        status, hdrs, body = self._invoke("GET")
        self.assertEqual(status, 200)
        self.assertEqual(hdrs.get("Content-Type"), "application/json")
        self.assertEqual(hdrs.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("max-age=30", hdrs.get("Cache-Control", ""))
        payload = json.loads(body)
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["ranked_accounts"])

    def test_get_returns_200_even_when_missing(self) -> None:
        status, _, body = self._invoke("GET", artifact_missing=True)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "degraded")

    def test_options_returns_204(self) -> None:
        status, hdrs, _ = self._invoke("OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(hdrs.get("Access-Control-Allow-Methods"), "GET, OPTIONS")


if __name__ == "__main__":
    unittest.main()
