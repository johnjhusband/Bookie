"""Monthly CPA-handoff cleanup pass.

Runs the standard pre-handoff checklist a CPA expects (per the design research):
  - recategorize anything sitting in Uncategorized / Ask My Accountant
  - move owner/partner draws out of expense into per-partner equity
  - flag personal-in-business charges for review (don't silently deduct)
  - flag loan payments for interest/principal split
  - net credit-card payments to the liability (don't double-count as expense)
  - flag vehicle/mileage for CPA method choice
  - scan vendors crossing the 2026 1099-NEC threshold ($2,000, non-card)

Pure function over a list of transactions + vendor payment totals → a
CleanupReport. No live QBO needed to exercise it; the live tick feeds it
real data and acts on the proposed reclassifications via qbo.reclassify_purchase.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from bookie.models import Transaction
from bookie.categorizer import categorize
from bookie.coa import COA_PATTERNS, classify_domain


# 2026 tax-year 1099-NEC threshold (OBBBA raised it from $600).
NEC_THRESHOLD_2026 = 2000.0

UNCATEGORIZED_ACCOUNTS = {"uncategorized expense", "uncategorized income",
                          "ask my accountant"}


@dataclass
class CleanupAction:
    tx_id: str
    vendor: str
    amount: float
    from_account: str
    to_account: str
    kind: str          # "recategorize" | "draw_to_equity" | "cc_netting"
    rationale: str


@dataclass
class CleanupFlag:
    tx_id: str
    vendor: str
    amount: float
    reason: str        # personal-in-business, loan-split, vehicle-method, etc.


@dataclass
class CleanupReport:
    period: str
    actions: list[CleanupAction] = field(default_factory=list)
    flags: list[CleanupFlag] = field(default_factory=list)
    nec_1099_vendors: list[dict] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (f"{len(self.actions)} reclassifications, {len(self.flags)} flagged "
                f"for review, {len(self.nec_1099_vendors)} 1099-NEC candidates")


def run_cleanup(period: str, transactions: list[Transaction], *,
                vendor_card_method: dict[str, str] | None = None,
                vendor_year_totals: dict[str, float] | None = None) -> CleanupReport:
    """Run the monthly cleanup pass. Pure.

    transactions: the period's posted transactions (with current account in raw['account_name']).
    vendor_card_method: {vendor: 'card'|'ach'|...} for 1099 eligibility (card excluded).
    vendor_year_totals: {vendor: ytd_non_card_paid} for the 1099 scan.
    """
    vendor_card_method = vendor_card_method or {}
    vendor_year_totals = vendor_year_totals or {}
    report = CleanupReport(period=period)

    for tx in transactions:
        current = (tx.raw or {}).get("account_name", "")
        cur_low = current.lower()

        # Domain rules first (draws, loans, CC payments, vehicle, estimated tax)
        hint = classify_domain(tx.vendor, tx.memo, tx.amount)
        if hint is not None:
            if hint.flag_for_review:
                report.flags.append(CleanupFlag(
                    tx.id, tx.vendor, tx.amount, hint.rationale))
            else:
                # a clean domain reclassification (e.g., draw → equity, CC netting)
                if hint.gl_account != current:
                    kind = ("cc_netting" if hint.gl_account == "Credit Card"
                            else "draw_to_equity" if "Draws" in hint.gl_account
                            else "recategorize")
                    report.actions.append(CleanupAction(
                        tx.id, tx.vendor, tx.amount, current, hint.gl_account,
                        kind, hint.rationale))
            continue

        # Then: anything still in an Uncategorized bucket gets recategorized
        if cur_low in UNCATEGORIZED_ACCOUNTS:
            cat = categorize(tx, coa_patterns=COA_PATTERNS, neighbors=transactions)
            if cat.gl_account and cat.gl_account != current:
                report.actions.append(CleanupAction(
                    tx.id, tx.vendor, tx.amount, current, cat.gl_account,
                    "recategorize",
                    f"chain step {cat.rule_chain_step} (conf {cat.confidence:.2f}): {cat.rationale}"))

    # 1099-NEC scan
    for vendor, total in vendor_year_totals.items():
        method = vendor_card_method.get(vendor, "ach")
        if method in ("card", "credit_card", "debit_card"):
            continue  # card payments are 1099-K, not NEC
        if total >= NEC_THRESHOLD_2026:
            report.nec_1099_vendors.append({"vendor": vendor, "total": total})

    return report


def render_cleanup_markdown(report: CleanupReport) -> str:
    lines = [f"# Monthly cleanup — {report.period}", "", f"_{report.summary}_", ""]
    if report.actions:
        lines.append("## Reclassifications applied")
        for a in report.actions:
            lines.append(f"- {a.tx_id} {a.vendor} ${abs(a.amount):.2f}: "
                         f"{a.from_account or '(none)'} → {a.to_account} ({a.kind}) — {a.rationale}")
        lines.append("")
    if report.flags:
        lines.append("## Flagged for review (not auto-changed)")
        for f in report.flags:
            lines.append(f"- {f.tx_id} {f.vendor} ${abs(f.amount):.2f}: {f.reason}")
        lines.append("")
    if report.nec_1099_vendors:
        lines.append("## 1099-NEC candidates (paid ≥ $2,000 non-card)")
        for v in report.nec_1099_vendors:
            lines.append(f"- {v['vendor']}: ${v['total']:.2f}")
    return "\n".join(lines)
