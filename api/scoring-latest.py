"""Public latest-scoring endpoint for the showcase deploy.

Stdlib-only Vercel Python serverless function. Serves the most recent scoring
run that the daily benchmark committed to the repo (``_scoring_latest.json``,
the git-as-database artifact). No database, no secrets: the file is the source
of truth, this function just reads and returns it.

The payload is honest about its provenance: ``dataset_kind: "synthetic-public"``
and a named ``fixture`` make clear the numbers come from a reproducible public
fixture, not live customer data. See:

  https://github.com/IgnazioDS/revenue-signal-copilot/tree/main/examples/fixtures
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

SYSTEM_SLUG = "revenue-signal-copilot"
SCHEMA_VERSION = 1
FIXTURE_ID = "synthetic-crm-v1"
DATASET_KIND = "synthetic-public"

ARTIFACT_FILE = Path(__file__).parent / "_scoring_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_artifact() -> dict[str, Any] | None:
    """Read the committed latest-scoring artifact, or None if unavailable."""
    try:
        data = json.loads(ARTIFACT_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _degraded_payload() -> dict[str, Any]:
    """A schema-valid, empty payload served when no artifact is present.

    The contract forbids 5xx; an empty-but-valid body keeps the consumer happy.
    """
    return {
        "system": SYSTEM_SLUG,
        "benchmark_type": "scoring",
        "mode": "live",
        "status": "degraded",
        "fixture": FIXTURE_ID,
        "dataset_kind": DATASET_KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "metrics": {
            "accounts_total": 0,
            "accounts_scored_24h": 0,
            "signals_detected_24h": 0,
            "high_priority_accounts": 0,
        },
        "calibration": None,
        "ranked_accounts": [],
        "top_signals": [],
        "previous_run": None,
    }


def build_response() -> dict[str, Any]:
    artifact = _load_artifact()
    if artifact is None:
        return _degraded_payload()
    # Serve the committed artifact (its generated_at reflects when the scoring
    # actually ran). benchmark_type is a constant for this endpoint, so force it
    # on every response — conformance must never depend on an older artifact that
    # predates the field.
    return {**artifact, "benchmark_type": "scoring"}


class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless entrypoint."""

    def _write_common_headers(self) -> None:
        self.send_header(
            "Cache-Control", "public, max-age=30, stale-while-revalidate=60"
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802 (interface contract)
        self.send_response(204)
        self._write_common_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 (interface contract)
        try:
            payload = build_response()
        except Exception:  # noqa: BLE001 (last-resort: contract forbids 5xx)
            payload = _degraded_payload()

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._write_common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002, ARG002
        return  # Suppress default access log; Vercel captures stdout/stderr.
