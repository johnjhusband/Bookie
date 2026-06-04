"""Bookie — an AI bookkeeper for QuickBooks Online.

Architecture:
  - The BRAIN is Claude, reasoning over each transaction with its context
    (bookie.brain — runs the `claude` CLI on the owner's subscription, no API key).
  - CODE does only PLUMBING: connect to QuickBooks Online, read transactions, and —
    once the owner approves — write a single change back (bookie.qbo).
  - There is no hardcoded categorization logic. That is intentional: the judgment
    is the LLM's, not a keyword script's.

Bookie is read-only on the books until the owner explicitly approves a change.
"""
from __future__ import annotations

__version__ = "0.2.0"
