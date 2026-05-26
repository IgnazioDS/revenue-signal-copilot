"""Revenue Signal Copilot package.

The showcase scaffold (``catalog`` / ``models`` / ``cli``), the local CSV
scoring MVP (``copilot``), and the daily public-benchmark layer (``scoring``,
``fixtures``, ``scoring_runner``) that publishes the committed scoring artifact.
"""

from .catalog import load_project
from .copilot import build_account_brief, load_signals_from_csv, score_accounts

__all__ = ["build_account_brief", "load_project", "load_signals_from_csv", "score_accounts"]
