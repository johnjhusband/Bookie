"""The decision chain that defines Bookie. PRD §4 + SOUL.md.

Pure function — no QBO writes, no chat.db logging here. Callers wrap the
returned Categorization in `policy.guard(action)` and persist accordingly.

Chain order (per SOUL.md):
1. QuickBooks Memorized Transactions — explicit upstream rule match
2. Transaction context — vendor / memo / amount pattern against locked CoA
3. Temporal context — surrounding transactions (transfer-pair, expense+reimbursement, recurring bill on schedule)
4. Historical similarity — past categorizations for same vendor or similar pattern
5. Default categorization with confidence tag — best guess + bookie-confidence=low
6. Escalate to Chief of Staff — only when none of the above produces a defensible answer

The chain stops at the FIRST step that produces a confident answer.
"""
from __future__ import annotations
from datetime import timedelta
from typing import Iterable, Optional

from bookie.models import Transaction, MemorizedRule, Categorization


# Confidence thresholds per chain step
_CONFIDENCE = {
    1: 1.00,   # QBO memorized = certain
    2: 0.90,   # context match
    3: 0.80,   # temporal correlation
    4: 0.75,   # historical similarity
    5: 0.40,   # default best-guess (low confidence)
    # step 6 = escalation, no confidence
}


def _match_memorized(tx: Transaction, rules: Iterable[MemorizedRule]) -> Optional[MemorizedRule]:
    """Step 1. Look for an explicit QBO memorized rule or learned rule."""
    vendor_lower = (tx.vendor or "").strip().lower()
    memo_lower = (tx.memo or "").strip().lower()
    for r in rules:
        if r.pattern_kind == "vendor_exact" and vendor_lower == r.pattern.lower():
            return r
        if r.pattern_kind == "vendor_prefix" and vendor_lower.startswith(r.pattern.lower()):
            return r
        if r.pattern_kind == "memo_contains" and r.pattern.lower() in memo_lower:
            return r
    return None


def _match_context(tx: Transaction, coa_patterns: dict[str, list[str]]) -> Optional[tuple[str, str]]:
    """Step 2. Pattern-match vendor / memo against locked Chart of Accounts.

    coa_patterns: { gl_account: [list of substrings that indicate this account] }
    Returns (gl_account, matched_pattern) or None.
    """
    needle = f"{tx.vendor} {tx.memo}".lower()
    for gl, patterns in coa_patterns.items():
        for p in patterns:
            if p.lower() in needle:
                return gl, p
    return None


def _match_temporal(tx: Transaction, neighbors: Iterable[Transaction]) -> Optional[tuple[str, str]]:
    """Step 3. Look at surrounding transactions for relationships.

    Detects:
    - transfer-pair: opposite-sign amount within ±$0.01 of |tx.amount| same day
    - expense+reimbursement: opposite-sign within ±2 days
    - recurring bill: same vendor charged monthly within ±3 days of tx.date - 30
    """
    abs_amt = abs(tx.amount)
    for n in neighbors:
        if n.id == tx.id:
            continue
        # transfer-pair (same day, opposite sign, same magnitude)
        if n.date == tx.date and abs(n.amount + tx.amount) < 0.01:
            return ("Account Transfers", f"transfer-pair with {n.id}")
        # expense+reimbursement (±2 days, opposite sign, same magnitude)
        if abs((n.date - tx.date).days) <= 2 and abs(n.amount + tx.amount) < 0.01:
            return ("Reimbursable Expenses", f"reimbursement pair with {n.id}")
        # recurring bill (same vendor, ~30 days prior)
        if (n.vendor == tx.vendor and n.amount * tx.amount > 0
                and 27 <= (tx.date - n.date).days <= 33):
            return ("Recurring", f"recurring monthly bill from {n.vendor}, last on {n.date}")
    return None


def _match_historical(tx: Transaction, history: Iterable[Categorization],
                       prior_lookup: dict[str, Transaction]) -> Optional[tuple[str, str]]:
    """Step 4. Look for prior categorizations of the same vendor.

    history: prior Categorization records
    prior_lookup: {transaction_id: Transaction} to resolve vendors from history
    Returns (gl_account, rationale) or None.
    """
    # Tally how often each GL was used for this vendor
    counts: dict[str, int] = {}
    for c in history:
        ptx = prior_lookup.get(c.transaction_id)
        if ptx and ptx.vendor.lower() == tx.vendor.lower():
            counts[c.gl_account] = counts.get(c.gl_account, 0) + 1
    if not counts:
        return None
    winner = max(counts, key=counts.get)
    return winner, f"vendor {tx.vendor!r} previously categorized as {winner} {counts[winner]} time(s)"


def _default_guess(tx: Transaction) -> tuple[str, str]:
    """Step 5. Last-resort default. Always succeeds (never None)."""
    if tx.amount > 0:
        return "Uncategorized Income", "no rule matched; default income bucket"
    return "Uncategorized Expense", "no rule matched; default expense bucket"


def categorize(
    tx: Transaction,
    *,
    memorized_rules: Iterable[MemorizedRule] = (),
    coa_patterns: dict[str, list[str]] | None = None,
    neighbors: Iterable[Transaction] = (),
    history: Iterable[Categorization] = (),
    prior_lookup: dict[str, Transaction] | None = None,
) -> Categorization:
    """Run the decision chain on one transaction.

    Returns a Categorization. requires_escalation is True only if EVERY step
    failed (in v1, step 5 always succeeds with a low-confidence default, so
    requires_escalation is set when the matchers below find nothing AND the
    transaction has explicit signals of unusualness — see _is_truly_stuck).
    """
    coa_patterns = coa_patterns or {}
    prior_lookup = prior_lookup or {}

    # Step 1: memorized
    rule = _match_memorized(tx, memorized_rules)
    if rule is not None:
        return Categorization(
            transaction_id=tx.id,
            gl_account=rule.gl_account,
            confidence=_CONFIDENCE[1],
            rule_chain_step=1,
            rationale=f"memorized rule matched ({rule.pattern_kind}={rule.pattern!r}, source={rule.source})",
        )

    # Step 2: CoA pattern
    ctx = _match_context(tx, coa_patterns)
    if ctx is not None:
        gl, pat = ctx
        return Categorization(
            transaction_id=tx.id,
            gl_account=gl,
            confidence=_CONFIDENCE[2],
            rule_chain_step=2,
            rationale=f"CoA pattern match on {pat!r}",
        )

    # Step 3: temporal context
    temp = _match_temporal(tx, neighbors)
    if temp is not None:
        gl, why = temp
        return Categorization(
            transaction_id=tx.id,
            gl_account=gl,
            confidence=_CONFIDENCE[3],
            rule_chain_step=3,
            rationale=why,
        )

    # Step 4: historical similarity
    hist = _match_historical(tx, history, prior_lookup)
    if hist is not None:
        gl, why = hist
        return Categorization(
            transaction_id=tx.id,
            gl_account=gl,
            confidence=_CONFIDENCE[4],
            rule_chain_step=4,
            rationale=why,
        )

    # Step 5: default best-guess
    gl, why = _default_guess(tx)
    return Categorization(
        transaction_id=tx.id,
        gl_account=gl,
        confidence=_CONFIDENCE[5],
        rule_chain_step=5,
        rationale=why + " [bookie-confidence=low]",
    )
    # Step 6 (escalation) is NEVER reached from this pure function; caller
    # decides whether the step-5 default is acceptable, based on `requires_escalation`
    # logic that lives outside the categorizer (e.g., amount > threshold AND new vendor).
