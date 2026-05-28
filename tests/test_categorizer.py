"""Tests for the categorization decision chain.

Per Bookie PRD §15.S1: "Bookie's wasn't-sure log has < 5 items per week."
These tests validate the decision chain stops at the right step.
"""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

# Allow running with `python -m pytest tests/` from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.categorizer import categorize
from bookie.models import MemorizedRule, Transaction


COA = {
    "Software & SaaS": ["notion", "github"],
    "Cloud Hosting": ["hetzner", "aws"],
}


def test_step1_memorized_wins():
    tx = Transaction(id="T1", date=date(2026, 5, 1), amount=-79.00, vendor="Notion")
    rules = [MemorizedRule(pattern_kind="vendor_exact", pattern="Notion", gl_account="Software & SaaS")]
    cat = categorize(tx, memorized_rules=rules, coa_patterns=COA)
    assert cat.rule_chain_step == 1
    assert cat.gl_account == "Software & SaaS"
    assert cat.confidence == 1.0
    assert not cat.requires_escalation


def test_step2_coa_match():
    tx = Transaction(id="T2", date=date(2026, 5, 1), amount=-100.00, vendor="Hetzner GmbH", memo="cloud hosting")
    cat = categorize(tx, coa_patterns=COA)
    assert cat.rule_chain_step == 2
    assert cat.gl_account == "Cloud Hosting"
    assert cat.confidence >= 0.9


def test_step3_transfer_pair_detected():
    t_in = Transaction(id="T-IN", date=date(2026, 5, 3), amount=500.00, vendor="ACH credit")
    t_out = Transaction(id="T-OUT", date=date(2026, 5, 3), amount=-500.00, vendor="ACH debit")
    cat = categorize(t_in, neighbors=[t_in, t_out])
    assert cat.rule_chain_step == 3
    assert cat.gl_account == "Account Transfers"


def test_step3_recurring_bill_detected():
    prior = Transaction(id="P1", date=date(2026, 4, 1), amount=-79.00, vendor="Notion")
    tx = Transaction(id="T2", date=date(2026, 5, 1), amount=-79.00, vendor="Notion")
    cat = categorize(tx, neighbors=[prior, tx])
    assert cat.rule_chain_step == 3
    assert "recurring" in cat.rationale.lower()


def test_step4_historical_similarity():
    from bookie.models import Categorization
    prior_tx = Transaction(id="P1", date=date(2026, 4, 1), amount=-50.00, vendor="ObscureVendor LLC")
    prior_cat = Categorization(
        transaction_id="P1", gl_account="Office Supplies", confidence=0.4,
        rule_chain_step=5, rationale="manual override",
    )
    tx = Transaction(id="T2", date=date(2026, 5, 1), amount=-50.00, vendor="ObscureVendor LLC")
    cat = categorize(
        tx,
        history=[prior_cat],
        prior_lookup={"P1": prior_tx},
    )
    assert cat.rule_chain_step == 4
    assert cat.gl_account == "Office Supplies"


def test_step5_default_low_confidence():
    tx = Transaction(id="T9", date=date(2026, 5, 4), amount=-42.50, vendor="Completely Unknown Vendor")
    cat = categorize(tx, coa_patterns=COA)
    assert cat.rule_chain_step == 5
    assert cat.confidence < 0.5
    assert "bookie-confidence=low" in cat.rationale
    # Critical: even at step 5, we PRODUCE A CATEGORIZATION. We never bail.
    assert cat.gl_account in ("Uncategorized Income", "Uncategorized Expense")
    assert not cat.requires_escalation


def test_never_returns_none():
    """Critical invariant: the chain ALWAYS returns a Categorization, never None.

    The whole point of the categorize-by-default rule is that John never has to
    look at individual transactions; every one gets a GL code, even if low confidence.
    """
    tx = Transaction(id="X", date=date(2026, 5, 5), amount=0.01, vendor="")
    cat = categorize(tx)
    assert cat is not None
    assert cat.gl_account != ""


def test_inflow_default_is_income_bucket():
    tx = Transaction(id="X", date=date(2026, 5, 5), amount=100.00, vendor="Unknown Source")
    cat = categorize(tx)
    assert cat.gl_account == "Uncategorized Income"


def test_outflow_default_is_expense_bucket():
    tx = Transaction(id="X", date=date(2026, 5, 5), amount=-100.00, vendor="Unknown Vendor")
    cat = categorize(tx)
    assert cat.gl_account == "Uncategorized Expense"
