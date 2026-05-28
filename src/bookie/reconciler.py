"""Bank-feed ↔ ledger reconciliation.

Daily skill. Given a list of bank-feed Transaction objects and a list of
ledger entries (from QBO), produce a match report.

Matching rules (in priority order):
1. Exact id match — feed line carries qbo_id from a prior write
2. Date + amount + memo substring
3. Date + amount, within ±2 days
4. Date + amount, within ±5 days (soft window for slow-posting)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Optional

from bookie.models import Transaction


@dataclass
class LedgerEntry:
    """A QBO JournalEntry / Bill / Payment / Deposit as seen from Plaid's side."""
    id: str               # QBO entity id
    date: date
    amount: float         # same sign convention as Transaction (positive=inflow)
    memo: str = ""
    account: str = ""     # QBO account name
    qbo_type: str = ""    # JournalEntry | Bill | Payment | Deposit


@dataclass
class MatchPair:
    feed_tx: Transaction
    ledger_entry: LedgerEntry
    rule: str             # which rule matched
    confidence: float


@dataclass
class ReconResult:
    account: str
    as_of: date
    feed_count: int
    ledger_count: int
    matched: list[MatchPair] = field(default_factory=list)
    unmatched_feed: list[Transaction] = field(default_factory=list)
    unmatched_ledger: list[LedgerEntry] = field(default_factory=list)

    @property
    def status(self) -> str:
        """clean | dirty | escalate."""
        unmatched_count = len(self.unmatched_feed) + len(self.unmatched_ledger)
        if unmatched_count == 0:
            return "clean"
        amounts = [abs(t.amount) for t in self.unmatched_feed] + \
                  [abs(e.amount) for e in self.unmatched_ledger]
        worst_amount = max(amounts) if amounts else 0.0
        if unmatched_count > 5 or worst_amount > 1000:
            return "escalate"
        return "dirty"


def _matches_exact_id(tx: Transaction, entry: LedgerEntry) -> bool:
    qbo_id = (tx.raw or {}).get("qbo_id")
    return bool(qbo_id) and qbo_id == entry.id


def _matches_date_amount_memo(tx: Transaction, entry: LedgerEntry) -> bool:
    if tx.date != entry.date:
        return False
    if abs(tx.amount - entry.amount) >= 0.01:
        return False
    if not tx.memo or not entry.memo:
        return False
    return tx.memo.lower()[:20] in entry.memo.lower() or entry.memo.lower()[:20] in tx.memo.lower()


def _matches_date_amount(tx: Transaction, entry: LedgerEntry, window_days: int) -> bool:
    if abs(tx.amount - entry.amount) >= 0.01:
        return False
    return abs((tx.date - entry.date).days) <= window_days


def match_feed_to_ledger(
    *,
    account: str,
    as_of: date,
    feed: Iterable[Transaction],
    ledger: Iterable[LedgerEntry],
) -> ReconResult:
    """Run the matching rules in priority order. Each match consumes both sides.

    Greedy: first rule that matches wins; entries are removed from the available
    pool. Order rules from most-specific to most-permissive.
    """
    feed_remaining = list(feed)
    ledger_remaining = list(ledger)
    matched: list[MatchPair] = []

    rules = [
        ("exact_id", lambda t, e: _matches_exact_id(t, e), 1.00),
        ("date_amount_memo", lambda t, e: _matches_date_amount_memo(t, e), 0.95),
        ("date_amount_0d", lambda t, e: _matches_date_amount(t, e, 0), 0.90),
        ("date_amount_2d", lambda t, e: _matches_date_amount(t, e, 2), 0.80),
        ("date_amount_5d", lambda t, e: _matches_date_amount(t, e, 5), 0.65),
    ]

    for rule_name, pred, conf in rules:
        # Iterate carefully — we modify both lists
        i = 0
        while i < len(feed_remaining):
            tx = feed_remaining[i]
            matched_entry = None
            for entry in ledger_remaining:
                if pred(tx, entry):
                    matched_entry = entry
                    break
            if matched_entry is not None:
                matched.append(MatchPair(tx, matched_entry, rule_name, conf))
                feed_remaining.pop(i)
                ledger_remaining.remove(matched_entry)
            else:
                i += 1

    return ReconResult(
        account=account,
        as_of=as_of,
        feed_count=sum(1 for _ in matched) + len(feed_remaining),
        ledger_count=sum(1 for _ in matched) + len(ledger_remaining),
        matched=matched,
        unmatched_feed=feed_remaining,
        unmatched_ledger=ledger_remaining,
    )
