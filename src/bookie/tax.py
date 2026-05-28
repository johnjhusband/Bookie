"""Tax-related preparation skills. v1: 1099-NEC packet generation.

Bookie generates the packet; John signs and files. Bookie never transmits
to the IRS.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable


# 2026 tax-year threshold for 1099-NEC (raised from $600 to $2,000)
NEC_THRESHOLD_2026 = 2000.00


@dataclass
class VendorPayments:
    vendor_id: str
    display_name: str
    tax_identifier: str = ""        # EIN or SSN from W-9
    address: str = ""
    payment_methods: dict[str, float] = field(default_factory=dict)
    total_eligible: float = 0.0     # sum of non-card payments
    payment_count: int = 0
    w9_on_file: bool = False


@dataclass
class PacketEntry:
    vendor: VendorPayments
    flags: list[str] = field(default_factory=list)


@dataclass
class PacketResult:
    tax_year: int
    threshold: float
    entries: list[PacketEntry]
    flagged_no_w9: list[VendorPayments]
    flagged_foreign: list[VendorPayments]
    flagged_ambiguous: list[VendorPayments]
    artifact_path: Path | None = None


def aggregate_vendor_payments(
    transactions: Iterable[dict],
    vendor_master: dict[str, dict],
) -> dict[str, VendorPayments]:
    """Roll up transactions by vendor.

    transactions: list of {vendor_id, amount, payment_method, date}
    vendor_master: {vendor_id: {display_name, tax_identifier, address, w9_on_file}}
    """
    out: dict[str, VendorPayments] = {}
    for t in transactions:
        vid = t.get("vendor_id")
        if not vid:
            continue
        vm = vendor_master.get(vid, {})
        if vid not in out:
            out[vid] = VendorPayments(
                vendor_id=vid,
                display_name=vm.get("display_name", vid),
                tax_identifier=vm.get("tax_identifier", ""),
                address=vm.get("address", ""),
                w9_on_file=bool(vm.get("w9_on_file")),
            )
        v = out[vid]
        amt = abs(float(t.get("amount", 0.0)))
        method = (t.get("payment_method", "") or "").lower()
        v.payment_methods[method] = v.payment_methods.get(method, 0.0) + amt
        v.payment_count += 1
        # Non-card payments are 1099-reportable; card payments are NOT
        # (the card processor issues a 1099-K instead).
        if method not in ("card", "credit_card", "debit_card"):
            v.total_eligible += amt
    return out


def generate_1099_packet(
    *,
    tax_year: int,
    transactions: Iterable[dict],
    vendor_master: dict[str, dict],
    workspace: Path,
) -> PacketResult:
    """Produce a 1099-NEC packet for vendors paid >= $2,000 via non-card methods.

    Writes the human-readable artifact to workspace/reports/1099-YYYY.md.
    Returns a structured PacketResult with flagged escalations.
    """
    payments = aggregate_vendor_payments(transactions, vendor_master)

    entries = []
    flagged_no_w9 = []
    flagged_foreign = []
    flagged_ambiguous = []

    # Group by tax_identifier to detect ambiguity (same EIN under two names)
    by_tin: dict[str, list[VendorPayments]] = {}
    for v in payments.values():
        if v.tax_identifier:
            by_tin.setdefault(v.tax_identifier, []).append(v)

    for v in payments.values():
        if v.total_eligible < NEC_THRESHOLD_2026:
            continue
        flags = []
        if not v.w9_on_file:
            flags.append("no_w9_on_file")
            flagged_no_w9.append(v)
        if v.tax_identifier and len(by_tin.get(v.tax_identifier, [])) > 1:
            flags.append("ambiguous_tin")
            flagged_ambiguous.append(v)
        # Foreign vendor detection — country code in address (simple heuristic)
        if v.address and not _looks_us(v.address):
            flags.append("possibly_foreign")
            flagged_foreign.append(v)
        entries.append(PacketEntry(vendor=v, flags=flags))

    # Write the human-readable artifact
    reports_dir = workspace / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifact = reports_dir / f"1099-{tax_year}.md"

    lines = [
        f"# 1099-NEC Packet — Tax Year {tax_year}\n",
        f"**Threshold:** ${NEC_THRESHOLD_2026:,.2f} (2026 rule)",
        f"**Forms required:** {len(entries)}",
        f"**Total reportable:** ${sum(e.vendor.total_eligible for e in entries):,.2f}\n",
        "## Filing deadlines\n",
        "- To recipient: Jan 31",
        "- To IRS (electronic): Jan 31",
        "- To IRS (paper): Feb 28\n",
        "## Vendors\n",
        "| Vendor | EIN/SSN | Address | Total Paid (non-card) | Flags |",
        "|--------|---------|---------|----------------------|-------|",
    ]
    for e in entries:
        flag_str = ", ".join(e.flags) if e.flags else "-"
        lines.append(
            f"| {e.vendor.display_name} | "
            f"{e.vendor.tax_identifier or 'MISSING'} | "
            f"{e.vendor.address[:40] or 'MISSING'} | "
            f"${e.vendor.total_eligible:,.2f} | {flag_str} |"
        )

    if flagged_no_w9:
        lines.append("\n## CoS escalation: missing W-9s\n")
        for v in flagged_no_w9:
            lines.append(f"- {v.display_name} (${v.total_eligible:,.2f}) — request W-9 before filing")

    if flagged_ambiguous:
        lines.append("\n## CoS escalation: ambiguous TINs\n")
        for v in flagged_ambiguous:
            lines.append(f"- {v.display_name} — same EIN {v.tax_identifier} under multiple vendor names")

    if flagged_foreign:
        lines.append("\n## CoS escalation: possibly-foreign vendors (1042-S not 1099-NEC?)\n")
        for v in flagged_foreign:
            lines.append(f"- {v.display_name} — address {v.address[:60]!r}")

    artifact.write_text("\n".join(lines))

    return PacketResult(
        tax_year=tax_year,
        threshold=NEC_THRESHOLD_2026,
        entries=entries,
        flagged_no_w9=flagged_no_w9,
        flagged_foreign=flagged_foreign,
        flagged_ambiguous=flagged_ambiguous,
        artifact_path=artifact,
    )


def _looks_us(address: str) -> bool:
    a = address.upper()
    # US state codes + ZIP heuristic
    us_signals = ["USA", "UNITED STATES", "U.S.A"]
    if any(s in a for s in us_signals):
        return True
    # 5-digit ZIP or ZIP+4
    import re
    if re.search(r"\b\d{5}(-\d{4})?\b", a):
        return True
    return False
