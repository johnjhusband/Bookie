"""Tests for the monthly CPA-handoff cleanup pass."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.models import Transaction
from bookie.cleanup import (run_cleanup, render_cleanup_markdown,
                            NEC_THRESHOLD_2026, CleanupReport)


def _tx(id, amount, vendor="", memo="", account_name=""):
    return Transaction(id=id, date=date(2026, 5, 1), amount=amount, vendor=vendor,
                       memo=memo, raw={"account_name": account_name})


def test_uncategorized_gets_recategorized():
    txs = [_tx("T1", -79.0, "Notion", "monthly", "Uncategorized Expense")]
    r = run_cleanup("2026-05", txs)
    assert len(r.actions) == 1
    a = r.actions[0]
    assert a.from_account == "Uncategorized Expense"
    assert a.to_account == "Software & Subscriptions"
    assert a.kind == "recategorize"


def test_owner_draw_moved_to_equity():
    txs = [_tx("T2", -5000.0, "Transfer", "John draw", "Owner Equity")]
    r = run_cleanup("2026-05", txs)
    assert any(a.kind == "draw_to_equity" and "John" in a.to_account for a in r.actions)


def test_loan_payment_flagged_not_actioned():
    txs = [_tx("T3", -1200.0, "Bank", "loan payment", "Loans")]
    r = run_cleanup("2026-05", txs)
    assert any("interest" in f.reason.lower() for f in r.flags)


def test_credit_card_payment_netted():
    txs = [_tx("T4", -2000.0, "Chase", "credit card payment thank you", "Bank Fees")]
    r = run_cleanup("2026-05", txs)
    assert any(a.kind == "cc_netting" and a.to_account == "Credit Card" for a in r.actions)


def test_vehicle_flagged_for_method_choice():
    txs = [_tx("T5", -300.0, "Auto", "vehicle expense", "Uncategorized Expense")]
    r = run_cleanup("2026-05", txs)
    assert any("mileage" in f.reason.lower() or "actual" in f.reason.lower() for f in r.flags)


def test_1099_scan_includes_over_threshold_non_card():
    txs = []
    r = run_cleanup("2026-12", txs,
                    vendor_card_method={"Contractor A": "ach", "Card Vendor": "card"},
                    vendor_year_totals={"Contractor A": 5000.0, "Card Vendor": 9000.0,
                                        "Small Fry": 500.0})
    names = [v["vendor"] for v in r.nec_1099_vendors]
    assert "Contractor A" in names          # over threshold, non-card
    assert "Card Vendor" not in names        # card payments are 1099-K
    assert "Small Fry" not in names          # under $2000


def test_threshold_is_2000():
    assert NEC_THRESHOLD_2026 == 2000.0


def test_already_categorized_not_touched():
    # a normal expense already in the right account, no domain rule → no action
    txs = [_tx("T6", -79.0, "Notion", "monthly", "Software & Subscriptions")]
    r = run_cleanup("2026-05", txs)
    assert r.actions == []
    assert r.flags == []


def test_render_markdown():
    txs = [_tx("T1", -79.0, "Notion", "monthly", "Uncategorized Expense")]
    r = run_cleanup("2026-05", txs)
    md = render_cleanup_markdown(r)
    assert "Monthly cleanup — 2026-05" in md
    assert "Notion" in md
