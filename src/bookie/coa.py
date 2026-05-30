"""Form-1065 partnership Chart of Accounts + domain categorization patterns.

Husband.LLC is a Florida husband-wife LLC → defaults to a Form 1065 partnership
(per IRS; Rev. Proc. 2002-69 disregarded-entity election is unavailable in
non-community-property states). Cash basis.

This module holds:
  - FORM_1065_COA: the canonical account structure a CPA expects, including
    per-partner equity (John and Tara each get Capital / Draws / Contributions).
  - COA_PATTERNS: vendor/memo substrings → GL account, for the categorizer's
    step-2 (context) match.
  - DOMAIN_RULES: the special-handling patterns that affect what the CPA sees
    (home office, vehicle, owner draws, mixed personal/business, estimated
    taxes, loan splits, credit-card payments). Each returns a categorization
    hint plus whether it should be flagged for review rather than silently
    posted.

Sources: AICPA Form 1065 checklist; IRS Pub 334/463/541; the Bookie design
research synthesis. See Bookie/lessons/ and prd/requirements.md (R6, R9, R10).
"""
from __future__ import annotations
from dataclasses import dataclass, field


PARTNERS = ["John Husband", "Tara Husband"]

# Canonical Form-1065 cash-basis CoA. Account name -> type. Bookie does not
# auto-create these; it uses what's in QBO and escalates if a needed account
# is missing. This is the reference the categorizer maps toward.
FORM_1065_COA: dict[str, str] = {
    # Assets
    "Cash": "Bank",
    "Accounts Receivable": "Accounts Receivable",
    "Undeposited Funds": "Other Current Asset",
    "Fixed Assets": "Fixed Asset",
    "Accumulated Depreciation": "Fixed Asset",
    # Liabilities
    "Accounts Payable": "Accounts Payable",
    "Credit Card": "Credit Card",
    "Loans Payable - Current": "Other Current Liability",
    "Loans Payable - Long Term": "Long Term Liability",
    "Payroll Liabilities": "Other Current Liability",
    # Equity — per partner (the 1065 structure)
    "John Husband Capital": "Equity",
    "John Husband Draws": "Equity",
    "John Husband Contributions": "Equity",
    "Tara Husband Capital": "Equity",
    "Tara Husband Draws": "Equity",
    "Tara Husband Contributions": "Equity",
    "Retained Earnings": "Equity",
    # Income
    "Sales": "Income",
    "Services": "Income",
    "Other Income": "Other Income",
    # Expenses (Schedule-C / 1065-aligned line items)
    "Advertising": "Expense",
    "Car & Truck": "Expense",
    "Commissions & Fees": "Expense",
    "Contract Labor": "Expense",
    "Depreciation": "Expense",
    "Employee Benefits": "Expense",
    "Insurance": "Expense",
    "Interest Expense": "Expense",
    "Legal & Professional": "Expense",
    "Office Expense": "Expense",
    "Rent or Lease": "Expense",
    "Repairs & Maintenance": "Expense",
    "Supplies": "Expense",
    "Taxes & Licenses": "Expense",
    "Travel": "Expense",
    "Meals": "Expense",
    "Utilities": "Expense",
    "Wages": "Expense",
    "Home Office - Utilities": "Expense",
    "Home Office - Rent": "Expense",
    "Home Office - Insurance": "Expense",
    "Account Transfers": "Other Current Asset",
    "Uncategorized Income": "Income",
    "Uncategorized Expense": "Expense",
}

# Vendor / memo substring -> GL account (step-2 context match).
COA_PATTERNS: dict[str, list[str]] = {
    "Software & Subscriptions": ["notion", "github", "openai", "anthropic", "claude",
                                  "linear", "1password", "atlassian", "cursor", "slack",
                                  "zoom", "adobe", "microsoft 365", "google workspace"],
    "Cloud Hosting": ["hetzner", "aws", "amazon web services", "digitalocean",
                       "cloudflare", "vercel", "render", "linode", "gcp", "azure"],
    "Meals": ["restaurant", "doordash", "uber eats", "grubhub", "starbucks", "cafe",
               "coffee", "pizza", "diner"],
    "Office Expense": ["staples", "office depot", "amzn", "amazon", "costco"],
    "Bank Fees": ["wire fee", "service charge", "atm fee", "overdraft", "nsf",
                   "monthly fee", "maintenance fee"],
    "Legal & Professional": ["attorney", "cpa", "consulting", "legal", "accountant",
                              "bookkeep", "law office"],
    "Travel": ["airlines", "hotel", "airbnb", "marriott", "hilton", "delta", "united",
                "american air", "rental car", "hertz", "avis"],
    "Car & Truck": ["shell", "chevron", "exxon", "gas station", "fuel", "auto repair",
                     "tire", "oil change"],
    "Insurance": ["insurance", "premium", "geico", "state farm", "progressive"],
    "Taxes & Licenses": ["irs", "state tax", "franchise tax", "dept of revenue",
                          "business license", "annual report fee"],
    "Advertising": ["facebook ads", "google ads", "meta", "mailchimp", "advertis"],
    "Utilities": ["electric", "water", "gas company", "internet", "comcast", "verizon",
                   "at&t", "t-mobile", "power company"],
}


@dataclass
class DomainHint:
    gl_account: str
    flag_for_review: bool = False
    rationale: str = ""


def classify_domain(vendor: str, memo: str, amount: float) -> DomainHint | None:
    """Apply the special-handling domain rules (R10). Returns a DomainHint or None.

    These rules affect what the CPA sees and so take priority over generic
    pattern matching when they fire.
    """
    text = f"{vendor} {memo}".lower()

    # Owner / partner draws → equity, never expense
    for partner in PARTNERS:
        first = partner.split()[0].lower()
        if f"draw" in text and first in text:
            return DomainHint(f"{partner} Draws", False,
                              f"owner draw to {partner} → equity, not expense")
    if "owner draw" in text or "member draw" in text or "distribution" in text:
        return DomainHint("John Husband Draws", True,
                          "owner draw/distribution → equity; confirm which partner")

    # Estimated quarterly tax payments → owner draws (not a business deduction)
    if ("estimated tax" in text or "irs estimated" in text or "1040-es" in text
            or "estimated payment" in text):
        return DomainHint("John Husband Draws", True,
                          "estimated income-tax payment → partner draw, not a business expense")

    # Home office expense portions
    if "home office" in text or ("rent" in text and "home" in text):
        return DomainHint("Home Office - Rent", False,
                          "home office portion → CPA applies % at filing")

    # Loan payment → must split interest (expense) vs principal (liability)
    if "loan payment" in text or "loan pmt" in text or ("loan" in text and "payment" in text):
        return DomainHint("Loans Payable - Current", True,
                          "loan payment → split interest (expense) / principal (liability) per amortization; escalate")

    # Credit card payment from checking → liability paydown, not expense
    if ("credit card payment" in text or "cc payment" in text
            or "card payment" in text or "payment thank you" in text):
        return DomainHint("Credit Card", False,
                          "credit-card payment → liability paydown, do not double-count as expense")

    # Vehicle / mileage note (Bookie can't track mileage; flag for CPA method choice)
    if any(k in text for k in ("mileage", "vehicle expense")):
        return DomainHint("Car & Truck", True,
                          "vehicle expense → CPA chooses standard mileage vs actual; Bookie does not track mileage")

    return None
