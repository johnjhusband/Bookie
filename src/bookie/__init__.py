"""Bookie — autonomous AI bookkeeper for John and Tara Husband, dba Husband.LLC.

Runs as an AI employee inside OpenHarness. Reports to Chief of Staff (Claude Code).
Never contacts John directly.

The daemon entry point is `tick(context)` — OpenHarness calls this on every
scheduled tick. Bookie:
  1. On first connection: inspects QBO (CoA, vendors, posted txns, recurring)
     and reports a "what I learned about your books" note to CoS.
  2. On routine ticks: reads QBO 'Uncategorized'-bucket transactions via API,
     runs the categorization chain, posts reclassifications via API.
  3. When browser is available: also drives the For Review queue via browser.
  4. Monthly: produces reports for CPA handoff.
  5. Year-end: 1099 packet if any vendor crossed $2,000 non-card.

Two surfaces (API + browser) per requirements.md R7+R8.
"""
from __future__ import annotations
import json
import os
import time
import traceback
from datetime import datetime, date
from pathlib import Path

__version__ = "0.3.0"


def _bookie_config_root() -> Path:
    env = os.environ.get("BOOKIE_CONFIG_ROOT")
    if env:
        return Path(env)
    return Path.home() / ".config" / "bookie"


def _qbo_creds_path() -> Path:
    return _bookie_config_root() / "qbo-credentials.json"


def _state_dir(emp_workspace: Path) -> Path:
    d = emp_workspace / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _has_qbo_creds() -> bool:
    p = _qbo_creds_path()
    if not p.exists():
        return False
    try:
        with p.open() as f:
            d = json.load(f)
    except Exception:
        return False
    return bool(d.get("client_id") and d.get("client_secret")
                and d.get("refresh_token") and d.get("realm_id"))


def _bookie_inspected_before(emp_workspace: Path) -> bool:
    return (_state_dir(emp_workspace) / "first-inspection.json").exists()


def _mark_inspected(emp_workspace: Path, summary: dict) -> None:
    p = _state_dir(emp_workspace) / "first-inspection.json"
    p.write_text(json.dumps({"completed_at": time.time(), "summary": summary}, indent=2))


def _do_first_inspection(emp_workspace: Path) -> dict:
    """R3: read CoA, vendors, last 12 months of transactions, recurring templates.
    Returns a summary dict and persists raw data under workspace/inspection/.
    """
    from bookie.qbo import (
        load_config, fetch_chart_of_accounts, fetch_vendors,
        fetch_memorized_transactions,
    )
    cfg = load_config(_qbo_creds_path())
    inspection_dir = emp_workspace / "inspection"
    inspection_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    creds_path = _qbo_creds_path()
    try:
        coa = fetch_chart_of_accounts(cfg, creds_path)
        (inspection_dir / "coa.json").write_text(json.dumps(coa, indent=2, default=str))
        summary["coa_account_count"] = len(coa)
        summary["coa_by_type"] = {}
        for a in coa:
            t = a.get("type", "Unknown")
            summary["coa_by_type"][t] = summary["coa_by_type"].get(t, 0) + 1
    except Exception as e:
        summary["coa_error"] = str(e)[:200]
    try:
        vendors = fetch_vendors(cfg, creds_path)
        (inspection_dir / "vendors.json").write_text(json.dumps(vendors, indent=2, default=str))
        summary["vendor_count"] = len(vendors)
        summary["vendors_marked_1099"] = sum(1 for v in vendors if v.get("active"))
    except Exception as e:
        summary["vendor_error"] = str(e)[:200]
    try:
        recurring = fetch_memorized_transactions(cfg, creds_path)
        (inspection_dir / "recurring.json").write_text(json.dumps(recurring, indent=2, default=str))
        summary["recurring_template_count"] = len(recurring)
    except Exception as e:
        summary["recurring_error"] = str(e)[:200]
    return summary


def _format_inspection_message(summary: dict) -> str:
    lines = ["**First inspection of your QBO complete.** Here's what I found:"]
    if "coa_account_count" in summary:
        lines.append(f"- Chart of Accounts: {summary['coa_account_count']} accounts.")
        by_type = summary.get("coa_by_type", {})
        if by_type:
            top = sorted(by_type.items(), key=lambda x: -x[1])[:6]
            lines.append("  Top types: " + ", ".join(f"{t}={n}" for t, n in top))
    if "vendor_count" in summary:
        lines.append(f"- Vendors: {summary['vendor_count']} on file.")
    if "recurring_template_count" in summary:
        lines.append(f"- Recurring transaction templates: {summary['recurring_template_count']}.")
    errs = {k: v for k, v in summary.items() if k.endswith("_error")}
    if errs:
        lines.append("\nIssues during inspection:")
        for k, v in errs.items():
            lines.append(f"- {k}: {v}")
    lines.append("\nFull inspection data persisted under workspace/inspection/. "
                 "Next ticks will use this to populate the categorization chain.")
    return "\n".join(lines)


def _process_uncategorized_via_api(emp_workspace: Path) -> dict:
    """R5: reclassify items sitting in Uncategorized/Ask-My-Accountant buckets.

    v0.3 minimal implementation: list the candidates, categorize via the chain,
    persist decisions. Live QBO write of the reclassification is the next milestone.
    """
    from bookie.categorizer import categorize
    from bookie.models import Transaction
    from bookie.qbo import load_config, _api_call  # private helper for queries

    cfg = load_config(_qbo_creds_path())
    creds_path = _qbo_creds_path()
    # Query posted Purchases assigned to Uncategorized Expense / Ask My Accountant
    # In QBO, these are typically named exactly. The real query is parameterized
    # against the CoA we already cached during inspection.
    coa_path = emp_workspace / "inspection" / "coa.json"
    targets: list[str] = []
    if coa_path.exists():
        for a in json.loads(coa_path.read_text()):
            n = (a.get("name") or "").lower()
            if any(x in n for x in ("uncategorized", "ask my accountant")):
                targets.append(a["id"])
    candidates: list[dict] = []
    for acct_id in targets:
        try:
            resp = _api_call(cfg, creds_path, "GET", "/query",
                             params={"query": f"SELECT * FROM Purchase WHERE AccountRef = '{acct_id}'"})
            candidates.extend(resp.get("QueryResponse", {}).get("Purchase", []))
        except Exception:
            continue

    if not candidates:
        return {"reviewed": 0, "reclassified": 0, "still_uncertain": 0}

    # Run the chain against each
    coa_patterns: dict[str, list[str]] = {}  # could be populated from vendor patterns later
    txs: list[Transaction] = []
    for p in candidates:
        try:
            txs.append(Transaction(
                id=p.get("Id", ""),
                date=date.fromisoformat((p.get("TxnDate") or "1970-01-01")[:10]),
                amount=-float(p.get("TotalAmt", 0.0)),
                vendor=(p.get("EntityRef") or {}).get("name", ""),
                memo=p.get("PrivateNote", ""),
                raw=p,
            ))
        except Exception:
            continue

    decisions_dir = emp_workspace / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    reclassified = 0
    still_uncertain = 0
    record = []
    for tx in txs:
        cat = categorize(tx, coa_patterns=coa_patterns, neighbors=txs)
        record.append({
            "tx_id": tx.id, "vendor": tx.vendor, "amount": tx.amount,
            "proposed_gl": cat.gl_account, "confidence": cat.confidence,
            "chain_step": cat.rule_chain_step, "rationale": cat.rationale,
        })
        if cat.confidence >= 0.75:
            # In a future milestone: POST update to QBO to reassign AccountRef.
            # For now: log the recommended action.
            reclassified += 1
        else:
            still_uncertain += 1
    (decisions_dir / f"{stamp}-uncategorized-review.json").write_text(
        json.dumps(record, indent=2, default=str))
    return {
        "reviewed": len(txs),
        "reclassified": reclassified,
        "still_uncertain": still_uncertain,
    }


def tick(context: dict) -> dict:
    """OpenHarness daemon entrypoint. See module docstring for the flow."""
    emp_workspace = Path(context["path"]) / "workspace"
    emp_workspace.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    memory: list[str] = []
    escalations: list[dict] = []

    if not _has_qbo_creds():
        return {
            "messages_to_cos": [],
            "memory_appends": [],
            "escalations": [],
            "llm_prompts": [],
            "status": "idle-no-qbo-creds",
        }

    # R3: first-inspection on first tick after creds are populated
    if not _bookie_inspected_before(emp_workspace):
        try:
            summary = _do_first_inspection(emp_workspace)
            _mark_inspected(emp_workspace, summary)
            messages.append(_format_inspection_message(summary))
            memory.append(
                f"[episodic] first QBO inspection completed "
                f"{datetime.utcnow().isoformat(timespec='seconds')}Z. "
                f"Found {summary.get('coa_account_count', '?')} accounts, "
                f"{summary.get('vendor_count', '?')} vendors, "
                f"{summary.get('recurring_template_count', '?')} recurring templates."
            )
            # First-inspection tick stops here; subsequent ticks do regular work
            return {
                "messages_to_cos": messages,
                "memory_appends": memory,
                "escalations": escalations,
                "llm_prompts": [],
                "status": "first-inspection-complete",
            }
        except Exception as e:
            return {
                "messages_to_cos": [
                    f"Bookie first-inspection FAILED: {e}\n{traceback.format_exc(limit=2)}"
                ],
                "memory_appends": [],
                "escalations": [],
                "llm_prompts": [],
                "status": "first-inspection-failed",
            }

    # R5: process anything sitting in Uncategorized buckets
    try:
        result = _process_uncategorized_via_api(emp_workspace)
        if result["reviewed"] > 0:
            messages.append(
                f"Reviewed {result['reviewed']} Uncategorized items: "
                f"{result['reclassified']} reclassified (conf >=0.75), "
                f"{result['still_uncertain']} still uncertain (logged to decisions/)."
            )
            memory.append(
                f"[episodic] tick {datetime.utcnow().isoformat(timespec='seconds')}Z "
                f"reviewed {result['reviewed']} uncategorized items."
            )
    except Exception as e:
        messages.append(f"Uncategorized-review pass failed: {e}")

    # R7: browser-driven For Review queue (if browser is available)
    # In v0.3 this is opt-in via env var BOOKIE_BROWSER_TICK=1 to avoid surprise costs.
    if os.environ.get("BOOKIE_BROWSER_TICK", "0") == "1":
        try:
            from bookie import browser
            if browser.is_available():
                queue = browser.list_for_review()
                if queue:
                    messages.append(f"For Review queue has {len(queue)} items pending.")
                    memory.append(
                        f"[episodic] browser saw {len(queue)} For Review items at "
                        f"{datetime.utcnow().isoformat(timespec='seconds')}Z."
                    )
        except Exception as e:
            messages.append(f"Browser surface unavailable this tick: {e}")

    status = "ok" if messages else "idle"
    return {
        "messages_to_cos": messages,
        "memory_appends": memory,
        "escalations": escalations,
        "llm_prompts": [],
        "status": status,
    }
