"""Tests for the anomaly sniff tests."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.models import Transaction
from bookie.anomaly import scan


def _tx(id, d, amount, vendor="", memo="", raw=None):
    return Transaction(id=id, date=d, amount=amount, vendor=vendor, memo=memo, raw=raw or {})


def test_round_number_outflow_flagged():
    tx = _tx("T", date(2026, 5, 1), -2000.00, vendor="Mystery LLC")
    r = scan(tx)
    assert "round_outflow" in r.flags


def test_small_round_number_not_flagged():
    tx = _tx("T", date(2026, 5, 1), -50.00, vendor="Notion")
    r = scan(tx)
    assert "round_outflow" not in r.flags


def test_after_hours_flag():
    tx = _tx("T", date(2026, 5, 1), -200.00, vendor="Late Night",
             raw={"authorized_datetime": "2026-05-01T03:30:00Z"})
    r = scan(tx)
    assert "after_hours" in r.flags


def test_duplicate_within_7d_flag():
    t1 = _tx("T1", date(2026, 5, 1), -123.45, vendor="Same Vendor")
    t2 = _tx("T2", date(2026, 5, 5), -123.45, vendor="Same Vendor")
    r = scan(t2, peers=[t1, t2])
    assert "duplicate_7d" in r.flags


def test_new_vendor_high_amount_flag():
    tx = _tx("T", date(2026, 5, 1), -750.00, vendor="Brand New Inc")
    r = scan(tx, known_vendors={"Notion", "GitHub"})
    assert "new_vendor_high_amount" in r.flags


def test_known_vendor_high_amount_not_flagged():
    tx = _tx("T", date(2026, 5, 1), -750.00, vendor="Notion")
    r = scan(tx, known_vendors={"Notion"})
    assert "new_vendor_high_amount" not in r.flags


def test_no_flags_for_normal_tx():
    tx = _tx("T", date(2026, 5, 1), -79.00, vendor="Notion")
    r = scan(tx, known_vendors={"Notion"})
    assert r.flags == []
    assert r.severity == "none"


def test_severity_escalates_with_count():
    tx = _tx("T", date(2026, 5, 1), -2000.00, vendor="Brand New",
             raw={"authorized_datetime": "2026-05-01T03:00:00Z"})
    r = scan(tx, known_vendors=set())  # new vendor + after_hours + round
    assert "round_outflow" in r.flags
    assert "after_hours" in r.flags
    assert "new_vendor_high_amount" in r.flags
    assert r.severity == "high"
