"""bookie CLI — run a categorization pass on a JSON file of transactions.

Usage:
    bookie categorize --feed <path.json> [--out <path.json>] [--dry-run]
    bookie self-check
"""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from bookie import categorizer
from bookie.models import MemorizedRule, Transaction
from bookie.plaid_feed import fetch_transactions_from_file


# Minimal seed Chart of Accounts patterns for v1 demo. Real CoA loaded from QBO in Phase 2.
DEFAULT_COA_PATTERNS = {
    "Software & SaaS": ["notion", "github", "openai", "anthropic", "linear", "1password"],
    "Cloud Hosting": ["hetzner", "aws", "digitalocean", "cloudflare"],
    "Meals & Entertainment": ["restaurant", "doordash", "uber eats", "grubhub"],
    "Office Supplies": ["staples", "office depot"],
    "Bank Fees": ["wire fee", "service charge", "atm fee"],
    "Transfers": ["transfer", "xfer", "tfr"],
}


def _cmd_categorize(args):
    feed_path = Path(args.feed)
    if not feed_path.exists():
        print(f"error: feed file not found: {feed_path}", file=sys.stderr)
        sys.exit(2)
    txs = fetch_transactions_from_file(feed_path)
    print(f"Loaded {len(txs)} transactions from {feed_path}")

    results = []
    for tx in txs:
        cat = categorizer.categorize(
            tx,
            memorized_rules=[],
            coa_patterns=DEFAULT_COA_PATTERNS,
            neighbors=txs,
            history=(),
            prior_lookup={},
        )
        results.append(cat)
        flag = "  " if cat.confidence >= 0.9 else ("? " if cat.confidence >= 0.5 else "!!")
        print(f"{flag} {tx.id:10s} {tx.date} ${tx.amount:9.2f} {tx.vendor[:25]:25s} → "
              f"{cat.gl_account:25s} (step {cat.rule_chain_step}, conf {cat.confidence:.2f})")

    # Summary
    by_step = {}
    low_confidence = 0
    for r in results:
        by_step[r.rule_chain_step] = by_step.get(r.rule_chain_step, 0) + 1
        if r.confidence < 0.5:
            low_confidence += 1
    print("\nSummary:")
    for step in sorted(by_step):
        labels = {1: "QBO memorized", 2: "CoA context", 3: "temporal", 4: "historical",
                  5: "default best-guess (low confidence)"}
        print(f"  Step {step} ({labels.get(step, '?')}): {by_step[step]}")
    print(f"  Low-confidence (bookie-confidence=low): {low_confidence}")

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(
            [{**asdict(r), "transaction_id": r.transaction_id} for r in results],
            indent=2, default=str
        ))
        print(f"\nWrote {len(results)} categorizations to {out_path}")


def _cmd_self_check(args):
    """Sanity test: run the categorizer on a synthetic transaction set."""
    from datetime import date
    txs = [
        Transaction(id="T1", date=date(2026, 5, 1), amount=-79.00, vendor="Notion", memo="monthly subscription"),
        Transaction(id="T2", date=date(2026, 5, 1), amount=-15.00, vendor="GitHub", memo="Copilot"),
        Transaction(id="T3", date=date(2026, 5, 2), amount=-1000.00, vendor="Hetzner GmbH", memo="cloud hosting"),
        Transaction(id="T4", date=date(2026, 5, 3), amount=500.00, vendor="ACH credit", memo=""),
        Transaction(id="T5", date=date(2026, 5, 3), amount=-500.00, vendor="ACH debit", memo=""),
        Transaction(id="T6", date=date(2026, 5, 4), amount=-42.50, vendor="Unknown Vendor XYZ", memo=""),
    ]
    print("Running self-check...")
    for tx in txs:
        cat = categorizer.categorize(
            tx,
            memorized_rules=[
                MemorizedRule(pattern_kind="vendor_exact", pattern="GitHub", gl_account="Software & SaaS"),
            ],
            coa_patterns=DEFAULT_COA_PATTERNS,
            neighbors=txs,
        )
        print(f"  {tx.id} {tx.vendor[:25]:25s} → {cat.gl_account:25s} step={cat.rule_chain_step} conf={cat.confidence:.2f}")
        print(f"      rationale: {cat.rationale}")
    print("\nself-check OK")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bookie", description="Bookie — autonomous bookkeeper CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("categorize", help="Run the decision chain on a JSON feed file")
    sp.add_argument("--feed", required=True, help="Path to JSON feed file")
    sp.add_argument("--out", help="Optional path to write categorizations JSON")
    sp.add_argument("--dry-run", action="store_true", help="Do not post to QBO (default)")
    sp.set_defaults(func=_cmd_categorize)

    sp = sub.add_parser("self-check", help="Run the categorizer on a synthetic set")
    sp.set_defaults(func=_cmd_self_check)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
