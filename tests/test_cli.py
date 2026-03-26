from __future__ import annotations

import unittest

from revenue_signal_copilot.cli import run


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
