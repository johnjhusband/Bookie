"""Tests for the bank-feed reconciler."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.models import Transaction
from bookie.reconciler import LedgerEntry, match_feed_to_ledger


def _tx(id, d, amount, vendor="", memo="", raw=None):
    return Transaction(id=id, date=d, amount=amount, vendor=vendor, memo=memo, raw=raw or {})


def _entry(id, d, amount, memo=""):
    return LedgerEntry(id=id, date=d, amount=amount, memo=memo, qbo_type="JournalEntry")


def test_clean_recon_all_match():
    feed = [_tx("F1", date(2026, 5, 1), -79.00, memo="Notion subscription"),
            _tx("F2", date(2026, 5, 2), -42.00, memo="GitHub")]
    ledger = [_entry("L1", date(2026, 5, 1), -79.00, "Notion subscription"),
              _entry("L2", date(2026, 5, 2), -42.00, "GitHub")]
    r = match_feed_to_ledger(account="checking-8211", as_of=date(2026, 5, 31),
                             feed=feed, ledger=ledger)
    assert r.status == "clean"
    assert len(r.matched) == 2
    assert len(r.unmatched_feed) == 0
    assert len(r.unmatched_ledger) == 0


def test_exact_id_wins():
    feed = [_tx("F1", date(2026, 5, 1), -100.00, raw={"qbo_id": "QBO-42"})]
    ledger = [_entry("QBO-42", date(2026, 5, 3), -100.00)]  # different date — exact id wins anyway
    r = match_feed_to_ledger(account="x", as_of=date(2026, 5, 31),
                             feed=feed, ledger=ledger)
    assert r.matched[0].rule == "exact_id"


def test_date_amount_window_2d():
    feed = [_tx("F1", date(2026, 5, 1), -50.00)]
    ledger = [_entry("L1", date(2026, 5, 3), -50.00)]   # 2 days off
    r = match_feed_to_ledger(account="x", as_of=date(2026, 5, 31),
                             feed=feed, ledger=ledger)
    assert r.status == "clean"


def test_dirty_few_small_mismatches():
    feed = [_tx("F1", date(2026, 5, 1), -50.00)]
    ledger = [_entry("L1", date(2026, 5, 1), -100.00)]  # amount mismatch
    r = match_feed_to_ledger(account="x", as_of=date(2026, 5, 31),
                             feed=feed, ledger=ledger)
    assert r.status == "dirty"
    assert len(r.unmatched_feed) == 1
    assert len(r.unmatched_ledger) == 1


def test_escalate_when_large_mismatch():
    feed = [_tx("F1", date(2026, 5, 1), -5000.00)]
    ledger = []   # nothing matches
    r = match_feed_to_ledger(account="x", as_of=date(2026, 5, 31),
                             feed=feed, ledger=ledger)
    assert r.status == "escalate"
