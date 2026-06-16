"""Public telemetry endpoint for the live scoring benchmark (Tier A).

Stdlib-only Vercel Python serverless function consumed by the Production
Telemetry panel on https://eleventh.dev. This system graduated from Tier B
(GitHub-derived showcase counters) to Tier A (``mode: "live"``) once the daily
scoring benchmark began producing a persistent, cold-start-durable artifact.

The Tier-A metrics describe real computation: the engine actually scored every
account in the committed fixture on the last run. The fixture is synthetic and
public (see ``dataset_kind`` on /api/scoring-latest), so the numbers are
reproducible and honest rather than simulated. The Tier-A metric shape is fixed
by the fleet contract:

  https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md

Source of truth is the git-committed artifact written by the nightly runner
(``_scoring_latest.json`` + ``_scoring_history.json``). Because the default
branch is ruleset-protected, the runner publishes to the unprotected
``telemetry`` branch; this endpoint reads the freshest copy from there at
request time (deployed runtime only) and falls back to the copy committed on
main. No database, no secrets.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

SYSTEM_SLUG = "revenue-signal-copilot"
SCHEMA_VERSION = 1

# The nightly cron publishes here because main is ruleset-protected.
_TELEMETRY_RAW_BASE = (
    "https://raw.githubusercontent.com/IgnazioDS/revenue-signal-copilot/telemetry/api/"
)
_FETCH_TIMEOUT_S = 2.5  # keep the endpoint fast; fall back to the committed copy

# Sanity caps: never expose values larger than these (runaway-exposure guard).
SAFETY_CAPS: dict[str, int] = {
    "accounts_total": 10_000_000,
    "accounts_scored_24h": 1_000_000,
    "signals_detected_24h": 1_000_000,
    "high_priority_accounts": 1_000_000,
}
TIER_A_METRIC_KEYS = tuple(SAFETY_CAPS)

SCORING_FILE = Path(__file__).parent / "_scoring_latest.json"
HISTORY_FILE = Path(__file__).parent / "_scoring_history.json"


def _cap(name: str, value: int) -> int:
    cap = SAFETY_CAPS.get(name)
    return min(value, cap) if cap is not None else value


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _fetch_remote_json(filename: str) -> dict[str, Any] | None:
    """Best-effort fetch of the freshest artifact from the telemetry data branch.

    Returns None on any failure so the caller falls back to the committed copy.
    Only runs in the deployed Vercel runtime; tests/local use the committed copy.
    """
    if not os.environ.get("VERCEL"):
        return None
    try:
        req = urllib.request.Request(
            _TELEMETRY_RAW_BASE + filename,
            headers={"User-Agent": f"{SYSTEM_SLUG}-telemetry"},
        )
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT_S) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 - the contract forbids 5xx; fall back instead
        return None


def _load_scoring() -> dict[str, Any] | None:
    return _fetch_remote_json("_scoring_latest.json") or _load_json(SCORING_FILE)


def _load_history() -> dict[str, Any] | None:
    return _fetch_remote_json("_scoring_history.json") or _load_json(HISTORY_FILE)


def _zeroed_metrics() -> dict[str, int]:
    return {key: 0 for key in TIER_A_METRIC_KEYS}


def _capped_metrics(raw: dict[str, Any]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for key in TIER_A_METRIC_KEYS:
        value = raw.get(key, 0)
        metrics[key] = _cap(key, int(value)) if isinstance(value, (int, float)) else 0
    return metrics


def _uptime_pct_30d(history: dict[str, Any] | None, now: datetime) -> float:
    """Share of expected daily runs that succeeded in the trailing 30 days.

    Method (documented in README): the runner only appends a history entry on a
    successful run, so success count is the number of runs in the window.
    Expected is one per day since the first run, capped at 30. A perfectly
    healthy daily cron reads ~100; missed days pull it down. Honest for a batch
    system that has no socket to ping.
    """
    runs = (history or {}).get("runs") or []
    timestamps = [
        ts for ts in (_parse_iso(r.get("as_of") or r.get("generated_at")) for r in runs)
        if ts is not None
    ]
    if not timestamps:
        return 0.0
    window_start = now - timedelta(days=30)
    runs_in_window = sum(1 for ts in timestamps if ts >= window_start)
    days_since_first = (now - min(timestamps)).days + 1
    expected = max(1, min(30, days_since_first))
    return round(min(100.0, 100.0 * runs_in_window / expected), 2)


def _build_response() -> dict[str, Any]:
    """Compose the Tier-A response. Always returns a parseable dict, never 5xx."""
    now = datetime.now(timezone.utc)
    scoring = _load_scoring()
    history = _load_history()
    static_deployed = os.environ.get("VERCEL_GIT_COMMIT_AUTHOR_DATE")

    if scoring is None:
        return {
            "system": SYSTEM_SLUG,
            "mode": "live",
            "workload": "benchmark",
            "status": "degraded",
            "last_deployed_at": static_deployed,
            "last_active_at": None,
            "uptime_pct_30d": _uptime_pct_30d(history, now),
            "metrics": _zeroed_metrics(),
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
        }

    raw_metrics = scoring.get("metrics") or {}
    last_active_at = scoring.get("generated_at")
    return {
        "system": SYSTEM_SLUG,
        "mode": "live",
        "workload": "benchmark",
        "status": "operational",
        "last_deployed_at": static_deployed or last_active_at,
        "last_active_at": last_active_at,
        "uptime_pct_30d": _uptime_pct_30d(history, now),
        "metrics": _capped_metrics(raw_metrics),
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
    }


class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless entrypoint.

    Vercel discovers this class by name; the runtime invokes ``do_GET`` /
    ``do_OPTIONS`` per the BaseHTTPRequestHandler protocol.
    """

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
            payload = _build_response()
        except Exception:  # noqa: BLE001 (last-resort: contract forbids 5xx)
            payload = {
                "system": SYSTEM_SLUG,
                "mode": "live",
                "workload": "benchmark",
                "status": "degraded",
                "last_deployed_at": None,
                "last_active_at": None,
                "uptime_pct_30d": 0.0,
                "metrics": _zeroed_metrics(),
                "schema_version": SCHEMA_VERSION,
                "generated_at": _now_iso(),
            }

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._write_common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002, ARG002
        return  # Suppress default access log; Vercel captures stdout/stderr.
