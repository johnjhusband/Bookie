"""Bookie — autonomous AI bookkeeper for John Husband's businesses.

Runs as an AI employee inside OpenHarness. Reports to Chief of Staff (Claude Code).
Never contacts John directly.

The daemon entry point is `tick(context)` — OpenHarness calls this on every
scheduled tick. Bookie does its deterministic work (categorize, reconcile),
returns any narrative-output prompts to the daemon for LLM composition.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, date
from pathlib import Path

__version__ = "0.1.0"


def _load_pending_feed(workspace: Path) -> list[dict]:
    """Look for a pending bank-feed file dropped by upstream (Plaid).

    v1 reads workspace/pending-feed.json if present.
    """
    candidate = workspace / "pending-feed.json"
    if not candidate.exists():
        return []
    try:
        return json.loads(candidate.read_text())
    except Exception:
        return []


def _archive_processed_feed(workspace: Path, processed: list[dict]) -> None:
    archive_dir = workspace / "processed-feeds"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (archive_dir / f"{stamp}.json").write_text(json.dumps(processed, indent=2))


def tick(context: dict) -> dict:
    """Called by OpenHarness daemon on each scheduled tick.

    Args:
        context: dict with keys name, path, openharness_root, inbox_path,
                 outbox_path, memory_path, heartbeat_path, now_ts.

    Returns:
        dict with messages_to_cos, memory_appends, escalations, llm_prompts, status.
    """
    from bookie.categorizer import categorize
    from bookie.models import Transaction

    emp_workspace = Path(context["path"]) / "workspace"
    emp_workspace.mkdir(parents=True, exist_ok=True)

    pending = _load_pending_feed(emp_workspace)
    if not pending:
        # Nothing scheduled and no pending feed; this tick is a no-op
        return {
            "messages_to_cos": [],
            "memory_appends": [],
            "escalations": [],
            "llm_prompts": [],
            "status": "idle",
        }

    # Convert raw feed entries to Transactions and run the chain
    txs = []
    for r in pending:
        try:
            txs.append(Transaction(
                id=r["id"],
                date=date.fromisoformat(r["date"]),
                amount=float(r["amount"]),
                vendor=r.get("vendor", ""),
                memo=r.get("memo", ""),
                account=r.get("account", ""),
                raw=r,
            ))
        except Exception:
            continue

    coa_patterns = {
        "Software & SaaS": ["notion", "github", "openai", "anthropic", "linear", "1password"],
        "Cloud Hosting": ["hetzner", "aws", "digitalocean", "cloudflare"],
        "Meals & Entertainment": ["restaurant", "doordash", "uber eats", "grubhub"],
        "Office Supplies": ["staples", "office depot"],
        "Bank Fees": ["wire fee", "service charge", "atm fee"],
    }

    categorizations = []
    by_step = {}
    low_confidence_items = []
    for tx in txs:
        cat = categorize(tx, coa_patterns=coa_patterns, neighbors=txs)
        categorizations.append((tx, cat))
        by_step[cat.rule_chain_step] = by_step.get(cat.rule_chain_step, 0) + 1
        if cat.confidence < 0.5:
            low_confidence_items.append((tx, cat))

    # Persist categorization decisions
    decisions_dir = emp_workspace / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (decisions_dir / f"{stamp}.json").write_text(json.dumps([
        {"tx_id": tx.id, "vendor": tx.vendor, "amount": tx.amount,
         "gl_account": cat.gl_account, "confidence": cat.confidence,
         "step": cat.rule_chain_step, "rationale": cat.rationale}
        for tx, cat in categorizations
    ], indent=2, default=str))

    _archive_processed_feed(emp_workspace, pending)
    # Clear the pending feed
    pending_path = emp_workspace / "pending-feed.json"
    if pending_path.exists():
        pending_path.unlink()

    summary_line = (
        f"Processed {len(txs)} transactions. By chain step: "
        + ", ".join(f"step{k}={v}" for k, v in sorted(by_step.items()))
        + f". Low-confidence: {len(low_confidence_items)}."
    )

    return {
        "messages_to_cos": [summary_line],
        "memory_appends": [
            f"[episodic] tick on {datetime.utcnow().isoformat(timespec='seconds')}Z "
            f"processed {len(txs)} transactions."
        ],
        "escalations": [],
        "llm_prompts": [],
        "status": "ok",
    }
