"""Anomaly / fraud sniff tests for incoming transactions.

Pattern-match rules, not LLM judgment. Determinism is the point — fraud
detection that's "AI-judged" is fraud detection that can't be audited.

Hits are independent; one transaction can hit multiple rules. Severity is
computed from flag count + amount.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from typing import Iterable

from bookie.models import Transaction


@dataclass
class AnomalyResult:
    tx_id: str
    flags: list[str] = field(default_factory=list)
    rationale: str = ""

    @property
    def severity(self) -> str:
        """low | medium | high."""
        n = len(self.flags)
        # Severity rules deferred to the orchestrator; this property is a
        # default for callers that don't supply per-rule weights.
        if n == 0:
            return "none"
        if n >= 3:
            return "high"
        if n >= 2:
            return "medium"
        return "low"


def _is_round_number(amount: float, threshold: float = 1000.0) -> bool:
    """True for amounts like $1000.00, $2500.00, $5000.00 above the threshold."""
    a = abs(amount)
    if a < threshold:
        return False
    return abs(a - round(a / 100) * 100) < 0.01 or abs(a - round(a / 500) * 500) < 0.01


def _is_after_hours(tx: Transaction) -> bool:
    """True if the transaction timestamp (if present in raw) is between 02:00 and 05:00."""
    raw = tx.raw or {}
    ts_str = raw.get("authorized_datetime") or raw.get("datetime")
    if not ts_str:
        return False
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return False
    return dtime(2, 0) <= dt.time() <= dtime(5, 0)


def _is_duplicate(tx: Transaction, peers: Iterable[Transaction]) -> bool:
    """True if another tx in the peer set has same vendor + same amount within 7 days."""
    for p in peers:
        if p.id == tx.id:
            continue
        if p.vendor != tx.vendor:
            continue
        if abs(p.amount - tx.amount) >= 0.01:
            continue
        if abs((p.date - tx.date).days) <= 7:
            return True
    return False


def _is_new_vendor_above(tx: Transaction, known_vendors: set[str],
                         threshold: float = 500.0) -> bool:
    if tx.vendor.lower() in {v.lower() for v in known_vendors}:
        return False
    return abs(tx.amount) > threshold


def _is_refund_without_origin(tx: Transaction, peers: Iterable[Transaction]) -> bool:
    """An inflow > $0 from a vendor with no prior matching-amount outflow in peers."""
    if tx.amount <= 0:
        return False
    for p in peers:
        if p.id == tx.id:
            continue
        if p.vendor != tx.vendor:
            continue
        if p.amount < 0 and abs(p.amount + tx.amount) < 0.01:
            return False  # found a matching outflow
    # Only flag if the amount is non-trivial
    return tx.amount >= 50.0


def scan(
    tx: Transaction,
    *,
    peers: Iterable[Transaction] = (),
    known_vendors: set[str] | None = None,
) -> AnomalyResult:
    """Run all sniff tests against one transaction. Returns flags and rationale."""
    known_vendors = known_vendors or set()
    peers_list = list(peers)
    flags = []
    rationales = []

    if _is_round_number(tx.amount):
        flags.append("round_outflow")
        rationales.append(f"amount ${abs(tx.amount):.2f} is a round number > $1000")

    if _is_after_hours(tx):
        flags.append("after_hours")
        rationales.append("transaction time 02:00-05:00 local")

    if _is_duplicate(tx, peers_list):
        flags.append("duplicate_7d")
        rationales.append(f"same vendor + amount within 7d of another tx")

    if _is_new_vendor_above(tx, known_vendors, 500.0):
        flags.append("new_vendor_high_amount")
        rationales.append(f"new vendor {tx.vendor!r} + amount > $500")

    if _is_refund_without_origin(tx, peers_list):
        flags.append("refund_no_origin")
        rationales.append("inflow with no matching prior outflow from same vendor")

    return AnomalyResult(
        tx_id=tx.id,
        flags=flags,
        rationale="; ".join(rationales),
    )
