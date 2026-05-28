"""Bookie — autonomous AI bookkeeper for John Husband's businesses.

Runs as an AI employee inside OpenHarness. Reports to Chief of Staff (Claude Code).
Never contacts John directly.

The daemon entry point is `tick(context)` — OpenHarness calls this on every
scheduled tick. Bookie pulls bank feeds (live if configured, else from a
dropped pending-feed.json), runs the categorization chain, persists decisions,
posts journal entries to QBO (if configured), and reports up.
"""
from __future__ import annotations
import json
import os
import time
import traceback
from datetime import datetime, date
from pathlib import Path

__version__ = "0.1.0"


def _bookie_config_root() -> Path:
    """Where bookie keeps its credentials. By default: $BOOKIE_CONFIG_ROOT or ~/.config/bookie/."""
    env = os.environ.get("BOOKIE_CONFIG_ROOT")
    if env:
        return Path(env)
    return Path.home() / ".config" / "bookie"


def _safe_load_pending_feed(workspace: Path) -> list[dict]:
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


def _try_pull_plaid(emp_workspace: Path) -> tuple[list[dict], list[str]]:
    """Try to pull live Plaid transactions. Returns (raw_feed_lines, errors).

    Returns ([], []) silently if Plaid isn't configured. Errors are non-fatal.
    """
    config_root = _bookie_config_root()
    creds_path = config_root / "plaid-credentials.json"
    items_path = config_root / "plaid-items.json"
    if not creds_path.exists() or not items_path.exists():
        return [], []
    try:
        from bookie.plaid_feed import load_config, load_items, save_items, fetch_transactions
    except Exception as e:
        return [], [f"plaid module import failed: {e}"]
    try:
        cfg = load_config(creds_path)
        items = load_items(items_path)
        all_lines = []
        updated_items = []
        for item in items:
            txs, updated = fetch_transactions(cfg, item)
            updated_items.append(updated)
            for tx in txs:
                all_lines.append({
                    "id": tx.id,
                    "date": tx.date.isoformat(),
                    "amount": tx.amount,
                    "vendor": tx.vendor,
                    "memo": tx.memo,
                    "account": tx.account,
                })
        save_items(updated_items, items_path)
        return all_lines, []
    except Exception as e:
        return [], [f"plaid fetch failed: {e}\n{traceback.format_exc(limit=2)}"]


def _try_post_to_qbo(categorizations: list, emp_workspace: Path) -> list[str]:
    """Try to post each categorization as a QBO journal entry.

    Returns list of error strings (empty if all posted or QBO not configured).
    Each post is wrapped in OpenHarness policy.guard (when available).
    """
    config_root = _bookie_config_root()
    creds_path = config_root / "qbo-credentials.json"
    if not creds_path.exists():
        return []
    errors = []
    try:
        from bookie.qbo import load_config, post_journal_entry, QBOError
        from openharness import policy as op_policy
    except Exception as e:
        return [f"qbo module import failed: {e}"]
    try:
        cfg = load_config(creds_path)
    except Exception as e:
        return [f"qbo config load failed: {e}"]
    posted_dir = emp_workspace / "posted"
    posted_dir.mkdir(parents=True, exist_ok=True)
    for tx, cat in categorizations:
        action = op_policy.Action(
            employee="bookie",
            kind="post_journal_entry",
            target=tx.id,
            amount=abs(tx.amount),
            description=f"{tx.vendor}: {cat.gl_account}",
        )
        try:
            with op_policy.guard(action):
                # Minimal QBO JournalEntry payload — real CoA mapping comes from
                # bookie.qbo.fetch_chart_of_accounts at startup; this stub uses a
                # placeholder until CoA cache is implemented in the next iteration.
                entry = {
                    "Line": [
                        {"Amount": abs(tx.amount), "DetailType": "JournalEntryLineDetail",
                         "JournalEntryLineDetail": {"PostingType": "Debit" if tx.amount < 0 else "Credit"},
                         "Description": cat.rationale[:200]},
                    ],
                }
                result = post_journal_entry(cfg, creds_path, entry)
                if not result.ok:
                    errors.append(f"qbo post {tx.id} failed: {result.error}")
                else:
                    (posted_dir / f"{tx.id}.json").write_text(
                        json.dumps({"request_id": result.request_id,
                                    "response": result.response}, indent=2)
                    )
        except op_policy.PolicyBypass as e:
            errors.append(f"policy blocked {tx.id}: {e}")
        except QBOError as e:
            errors.append(f"qbo error {tx.id}: {e}")
        except Exception as e:
            errors.append(f"unexpected error {tx.id}: {e}")
    return errors


def tick(context: dict) -> dict:
    """Called by OpenHarness daemon on each scheduled tick.

    Flow:
    1. Pull live Plaid transactions if configured; merge with any pending-feed.json
    2. Run the categorization chain on each
    3. Persist decisions to workspace/decisions/
    4. Try to post journal entries to QBO if configured (each through policy.guard)
    5. Return tick result for OpenHarness daemon to apply
    """
    from bookie.categorizer import categorize
    from bookie.models import Transaction

    emp_workspace = Path(context["path"]) / "workspace"
    emp_workspace.mkdir(parents=True, exist_ok=True)

    # 1. Collect transactions: live Plaid first, then any manual drop
    plaid_lines, plaid_errors = _try_pull_plaid(emp_workspace)
    manual_lines = _safe_load_pending_feed(emp_workspace)
    raw = plaid_lines + manual_lines

    if not raw:
        return {
            "messages_to_cos": [],
            "memory_appends": [],
            "escalations": [],
            "llm_prompts": [],
            "status": "idle" if not plaid_errors else "idle-with-errors",
        }

    # 2. Build Transactions and categorize
    txs = []
    for r in raw:
        try:
            txs.append(Transaction(
                id=r["id"],
                date=date.fromisoformat(r["date"]) if isinstance(r["date"], str) else r["date"],
                amount=float(r["amount"]),
                vendor=r.get("vendor", ""),
                memo=r.get("memo", ""),
                account=r.get("account", ""),
                raw=r,
            ))
        except Exception:
            continue

    coa_patterns = {
        "Software & SaaS": ["notion", "github", "openai", "anthropic", "linear", "1password",
                            "atlassian", "claude", "cursor"],
        "Cloud Hosting": ["hetzner", "aws", "digitalocean", "cloudflare", "vercel", "render"],
        "Meals & Entertainment": ["restaurant", "doordash", "uber eats", "grubhub", "starbucks"],
        "Office Supplies": ["staples", "office depot", "amzn", "amazon"],
        "Bank Fees": ["wire fee", "service charge", "atm fee", "overdraft", "nsf"],
        "Professional Services": ["attorney", "cpa", "consulting", "legal"],
        "Travel": ["uber", "lyft", "airlines", "hotel", "airbnb", "marriott", "hilton"],
        "Insurance": ["insurance", "premium"],
        "Taxes": ["irs", "state tax", "franchise tax"],
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

    # 3. Persist decisions
    decisions_dir = emp_workspace / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (decisions_dir / f"{stamp}.json").write_text(json.dumps([
        {"tx_id": tx.id, "vendor": tx.vendor, "amount": tx.amount,
         "date": tx.date.isoformat(), "gl_account": cat.gl_account,
         "confidence": cat.confidence, "step": cat.rule_chain_step,
         "rationale": cat.rationale}
        for tx, cat in categorizations
    ], indent=2))

    # 4. Archive manual feed; clear it
    if manual_lines:
        _archive_processed_feed(emp_workspace, manual_lines)
        pending_path = emp_workspace / "pending-feed.json"
        if pending_path.exists():
            pending_path.unlink()

    # 5. Try posting to QBO (if configured)
    qbo_errors = _try_post_to_qbo(categorizations, emp_workspace)

    # 6. Compose tick result
    summary_parts = [
        f"Processed {len(txs)} transactions",
        f"({len(plaid_lines)} from Plaid live)" if plaid_lines else "",
        f"({len(manual_lines)} from manual drop)" if manual_lines else "",
        ". By chain step: " + ", ".join(f"step{k}={v}" for k, v in sorted(by_step.items())),
        f". Low-confidence: {len(low_confidence_items)}.",
    ]
    summary_line = "".join(p for p in summary_parts if p)

    messages = [summary_line]
    if plaid_errors:
        messages.append("Plaid errors this tick: " + "; ".join(plaid_errors)[:500])
    if qbo_errors:
        messages.append("QBO posting errors: " + "; ".join(qbo_errors)[:500])

    escalations = []
    high_value_low_conf = [
        (tx, cat) for tx, cat in low_confidence_items if abs(tx.amount) > 1000
    ]
    for tx, cat in high_value_low_conf:
        escalations.append({
            "summary": f"Bookie low-confidence on high-value tx {tx.id} "
                       f"(${abs(tx.amount):.2f}, vendor={tx.vendor!r})",
            "body": f"Categorized as {cat.gl_account} at chain step {cat.rule_chain_step}. "
                    f"Rationale: {cat.rationale}",
            "recommendation": "Confirm the GL code or supply a memorized rule for this vendor.",
        })

    memory_entries = [
        f"[episodic] tick {datetime.utcnow().isoformat(timespec='seconds')}Z "
        f"processed {len(txs)} transactions "
        f"(plaid={len(plaid_lines)}, manual={len(manual_lines)}, qbo_errors={len(qbo_errors)})."
    ]

    return {
        "messages_to_cos": messages,
        "memory_appends": memory_entries,
        "escalations": escalations,
        "llm_prompts": [],
        "status": "ok" if not (plaid_errors or qbo_errors) else "ok-with-errors",
    }
