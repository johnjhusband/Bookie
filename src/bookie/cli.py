"""bookie CLI — read the live books and let Claude (Bookie's brain) review them.

Usage:
    bookie company                 # company profile (proves it's on the real books)
    bookie coa                     # chart of accounts
    bookie uncategorized           # count transactions in uncategorized buckets
    bookie review                  # Claude proposes a category for each uncategorized txn (READ-ONLY)

All judgment is done by Claude via bookie.brain (the `claude` CLI, on the owner's
subscription). Code only does plumbing: read from QBO, hand to Claude, relay.
Nothing is ever written to the books by these commands.
Credentials: ~/.config/bookie/qbo-credentials.json (override with $BOOKIE_QBO_CREDS).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path


def _creds_path() -> Path:
    env = os.environ.get("BOOKIE_QBO_CREDS")
    return Path(env) if env else Path.home() / ".config" / "bookie" / "qbo-credentials.json"


def _live():
    """Load the live QBO config. All live reads go through Bookie's own qbo client."""
    from bookie import qbo
    p = _creds_path()
    if not p.exists():
        print(f"error: QBO credentials not found at {p}", file=sys.stderr)
        sys.exit(2)
    return qbo, qbo.load_config(p), p


def _cmd_company(args):
    qbo, cfg, p = _live()
    print(json.dumps(qbo.fetch_company_info(cfg, p), indent=2))


def _cmd_coa(args):
    qbo, cfg, p = _live()
    accts = qbo.fetch_chart_of_accounts(cfg, p)
    print(f"{len(accts)} accounts")
    for a in sorted(accts, key=lambda x: (x.get("type") or "", x.get("name") or "")):
        print(f"  {a['name']} | {a['type']} | active={a['active']}")


def _cmd_uncategorized(args):
    qbo, cfg, p = _live()
    r = qbo.count_uncategorized(cfg, p)
    print(f"Uncategorized buckets: {r['accounts']}")
    for k, v in r["per_account"].items():
        print(f"  {k}: {v}")
    print(f"TOTAL uncategorized transactions: {r['total']}")


def _cmd_review(args):
    """Claude (Bookie's brain) reviews each uncategorized transaction. READ-ONLY."""
    from bookie import brain
    qbo, cfg, p = _live()
    if not brain.claude_available():
        print("error: the `claude` CLI is not available here — Bookie's brain needs it to reason. "
              "Install/authenticate Claude Code on this machine.", file=sys.stderr)
        sys.exit(3)
    accounts = qbo.fetch_chart_of_accounts(cfg, p)
    rows = qbo.fetch_uncategorized_transactions(cfg, p)
    print(f"Bookie (Claude) is reviewing {len(rows)} uncategorized transactions — read-only, proposals only:\n")
    props = brain.categorize_batch(rows, accounts)
    proposals = list(zip(rows, props))
    for r, prop in proposals:
        flag = "OK" if prop.confidence >= 0.8 else ("? " if prop.confidence >= 0.5 else "!!")
        amt = r.get("amount", "")
        print(f" {flag} {str(r.get('date',''))[:10]}  {str(amt):>12}  {(r.get('name') or '')[:24]:24} -> "
              f"{prop.account}  (conf {prop.confidence:.2f})")
        print(f"      {prop.rationale}")
    if args.out:
        Path(args.out).write_text(json.dumps(
            [{"txn": r, "account": p.account, "confidence": p.confidence, "rationale": p.rationale}
             for r, p in proposals], indent=2, default=str))
        print(f"\nWrote {len(proposals)} proposals to {args.out} (no changes posted to QuickBooks).")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bookie", description="Bookie — AI bookkeeper (Claude is the brain)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("company", help="Read the connected company profile (live)").set_defaults(func=_cmd_company)
    sub.add_parser("coa", help="Read the chart of accounts (live)").set_defaults(func=_cmd_coa)
    sub.add_parser("uncategorized", help="Count transactions in uncategorized buckets (live)").set_defaults(func=_cmd_uncategorized)
    rv = sub.add_parser("review", help="Claude proposes a category for each uncategorized txn (READ-ONLY)")
    rv.add_argument("--out", help="Optional path to write proposals JSON (still posts nothing)")
    rv.set_defaults(func=_cmd_review)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
