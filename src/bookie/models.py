"""Bookie domain model dataclasses. Pure data, no I/O."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


@dataclass(frozen=True)
class Transaction:
    """One bank-feed or QBO transaction awaiting categorization."""
    id: str                      # external id from the feed
    date: date
    amount: float                # positive = inflow, negative = outflow
    vendor: str                  # raw vendor / merchant string from the feed
    memo: str = ""
    account: str = ""            # bank account name / id this transaction posted to
    raw: dict = field(default_factory=dict)  # full upstream payload for debug


@dataclass(frozen=True)
class MemorizedRule:
    """A QuickBooks Memorized Transaction or our own learned rule."""
    pattern_kind: Literal["vendor_exact", "vendor_prefix", "memo_contains", "amount_range"]
    pattern: str
    gl_account: str
    source: Literal["qbo_memorized", "bookie_learned"] = "bookie_learned"
    confidence: float = 1.0


@dataclass(frozen=True)
class Categorization:
    """The result of running the decision chain on a transaction."""
    transaction_id: str
    gl_account: str
    confidence: float                  # 0.0 - 1.0
    rule_chain_step: int               # 1-6 per SOUL.md decision chain
    rationale: str
    requires_escalation: bool = False  # True iff the chain reached step 6 (ask CoS)
    proposed_journal_entry: dict | None = None
