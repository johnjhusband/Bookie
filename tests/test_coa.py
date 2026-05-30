"""Tests for the Form-1065 CoA + domain categorization rules."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.coa import (FORM_1065_COA, COA_PATTERNS, PARTNERS,
                        classify_domain, DomainHint)


def test_per_partner_equity_accounts_present():
    # 1065 needs Capital/Draws/Contributions per partner
    for p in PARTNERS:
        assert f"{p} Capital" in FORM_1065_COA
        assert f"{p} Draws" in FORM_1065_COA
        assert f"{p} Contributions" in FORM_1065_COA
        assert FORM_1065_COA[f"{p} Draws"] == "Equity"


def test_owner_draw_goes_to_equity_not_expense():
    hint = classify_domain("Transfer to John", "monthly draw", -5000)
    assert hint is not None
    assert "Draws" in hint.gl_account
    assert "John" in hint.gl_account


def test_generic_owner_draw_flags_for_review():
    hint = classify_domain("ACH", "owner draw", -3000)
    assert hint is not None
    assert "Draws" in hint.gl_account
    assert hint.flag_for_review is True


def test_estimated_tax_is_draw_not_expense():
    hint = classify_domain("IRS", "1040-ES estimated tax", -8000)
    assert hint is not None
    assert "Draws" in hint.gl_account
    assert hint.flag_for_review is True


def test_loan_payment_flagged_for_split():
    hint = classify_domain("Bank", "loan payment", -1200)
    assert hint is not None
    assert hint.flag_for_review is True
    assert "interest" in hint.rationale.lower()


def test_credit_card_payment_is_liability_not_expense():
    hint = classify_domain("Chase", "credit card payment thank you", -2000)
    assert hint is not None
    assert hint.gl_account == "Credit Card"
    assert hint.flag_for_review is False


def test_home_office_categorized_for_cpa_percentage():
    hint = classify_domain("Landlord", "home office rent", -800)
    assert hint is not None
    assert "Home Office" in hint.gl_account


def test_vehicle_expense_flags_method_choice():
    hint = classify_domain("Auto", "vehicle expense", -300)
    assert hint is not None
    assert hint.gl_account == "Car & Truck"
    assert hint.flag_for_review is True


def test_normal_expense_returns_no_domain_hint():
    # A plain software charge isn't a special domain case
    assert classify_domain("Notion", "monthly subscription", -79) is None


def test_coa_patterns_cover_common_vendors():
    # sanity: each pattern list is non-empty and maps to a known account
    for account, needles in COA_PATTERNS.items():
        assert needles, f"{account} has no patterns"
