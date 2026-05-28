"""Month-end close workflow.

Multi-step long-running task. Uses OpenHarness checkpoint primitive so a crash
mid-close can resume. Every QBO write goes through OpenHarness policy.guard.

Steps:
1. feeds-pulled: final bank feeds for the closing month
2. recon-complete: reconciliation pass; escalate any unmatched items
3. accruals-drafted: accrual entries (vendor bills received post-period)
4. prepaids-drafted: prepaid amortization
5. depreciation-drafted: depreciation entries
6. tb-drafted: draft trial balance + P&L
7. awaiting-signoff: notify CoS, pause
8. posted: on CoS approval, post all entries to QBO
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

# OpenHarness checkpoint is imported lazily so this module can be tested
# without OpenHarness on the import path.


@dataclass
class CloseContext:
    """Inputs to the close workflow."""
    closing_month: str          # "2026-04"
    workspace: Path             # employee workspace dir
    qbo_config_path: Optional[Path] = None
    plaid_config_path: Optional[Path] = None
    dry_run: bool = False       # if True, skip the QBO posting step


@dataclass
class CloseResult:
    task_id: str
    status: str                 # "complete" | "awaiting_signoff" | "escalated" | "failed"
    artifact_path: Optional[Path] = None
    entries_posted: int = 0
    errors: list[str] = field(default_factory=list)
    escalations: list[dict] = field(default_factory=list)


def _checkpoint():
    """Lazy import — returns OpenHarness checkpoint module or None."""
    try:
        from openharness import checkpoint
        return checkpoint
    except Exception:
        return None


def _save_step(task_id: str, step: str, state: dict) -> None:
    cp = _checkpoint()
    if cp is None:
        return
    cp.save(task_id, step, state)


def _complete(task_id: str) -> None:
    cp = _checkpoint()
    if cp is None:
        return
    cp.complete(task_id)


def _step_pull_feeds(ctx: CloseContext) -> dict:
    """Step 1. Snapshot whatever feeds we have for the closing month.

    v1: assume Plaid was running continuously during the month; just record
    a marker that we've reached the close cutoff. Real implementation could
    do a forced /transactions/sync here.
    """
    return {"step": "feeds-pulled", "closing_month": ctx.closing_month, "ts": time.time()}


def _step_recon(ctx: CloseContext) -> tuple[dict, list[dict]]:
    """Step 2. Run reconciliation. Returns (state, escalations).

    v1: minimal stub state. Real implementation calls bookie.reconciler against
    every connected account for the closing month and aggregates results.
    """
    escalations: list[dict] = []
    state = {"step": "recon-complete", "accounts_clean": 0, "accounts_dirty": 0}
    # When wired, populate escalations from reconciler.ReconResult.status == "escalate"
    return state, escalations


def _step_accruals(ctx: CloseContext) -> dict:
    """Step 3. Draft accrual entries."""
    drafts_dir = ctx.workspace / "drafts" / ctx.closing_month
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "accruals.json").write_text(json.dumps([], indent=2))
    return {"step": "accruals-drafted", "draft_path": str(drafts_dir / "accruals.json")}


def _step_prepaids(ctx: CloseContext) -> dict:
    """Step 4. Draft prepaid amortization."""
    drafts_dir = ctx.workspace / "drafts" / ctx.closing_month
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "prepaids.json").write_text(json.dumps([], indent=2))
    return {"step": "prepaids-drafted", "draft_path": str(drafts_dir / "prepaids.json")}


def _step_depreciation(ctx: CloseContext) -> dict:
    """Step 5. Draft depreciation entries."""
    drafts_dir = ctx.workspace / "drafts" / ctx.closing_month
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "depreciation.json").write_text(json.dumps([], indent=2))
    return {"step": "depreciation-drafted", "draft_path": str(drafts_dir / "depreciation.json")}


def _step_tb(ctx: CloseContext) -> tuple[dict, Path]:
    """Step 6. Produce draft trial balance + P&L. Returns (state, artifact_path)."""
    reports_dir = ctx.workspace / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifact = reports_dir / f"{ctx.closing_month}-close.md"
    artifact.write_text(
        f"# Month-end close — {ctx.closing_month}\n\n"
        f"## Executive summary\n\nDraft close package for {ctx.closing_month}. "
        f"Awaiting Chief of Staff sign-off.\n\n"
        f"## Trial balance\n\n_(populated when QBO data is wired)_\n\n"
        f"## P&L\n\n_(populated when QBO data is wired)_\n\n"
        f"## Drafted entries\n\n"
        f"- Accruals: drafts/{ctx.closing_month}/accruals.json\n"
        f"- Prepaids: drafts/{ctx.closing_month}/prepaids.json\n"
        f"- Depreciation: drafts/{ctx.closing_month}/depreciation.json\n"
    )
    return {"step": "tb-drafted", "artifact_path": str(artifact)}, artifact


def _step_post(ctx: CloseContext) -> tuple[dict, int, list[str]]:
    """Step 8. Post all drafted entries to QBO via policy.guard."""
    if ctx.dry_run:
        return {"step": "posted", "skipped": True, "reason": "dry_run"}, 0, []
    if ctx.qbo_config_path is None or not ctx.qbo_config_path.exists():
        return {"step": "posted", "skipped": True, "reason": "no_qbo_config"}, 0, []
    # Real posting: iterate accruals/prepaids/depreciation, post each via
    # bookie.qbo.post_journal_entry wrapped in OpenHarness policy.guard.
    # v1 returns a stub; the wiring is identical to bookie.__init__._try_post_to_qbo.
    return {"step": "posted"}, 0, []


def run_month_end_close(ctx: CloseContext) -> CloseResult:
    """Run the full close workflow with checkpoints between steps.

    Returns CloseResult.status="awaiting_signoff" after step 6 — close pauses
    here for Chief of Staff approval. After approval is detected (separately),
    run_post_step() picks up at step 8.
    """
    task_id = f"close-{ctx.closing_month}"
    errors: list[str] = []
    escalations: list[dict] = []

    s = _step_pull_feeds(ctx)
    _save_step(task_id, "feeds-pulled", s)

    s, ec = _step_recon(ctx)
    escalations.extend(ec)
    _save_step(task_id, "recon-complete", s)
    if escalations:
        return CloseResult(task_id=task_id, status="escalated", escalations=escalations)

    s = _step_accruals(ctx)
    _save_step(task_id, "accruals-drafted", s)

    s = _step_prepaids(ctx)
    _save_step(task_id, "prepaids-drafted", s)

    s = _step_depreciation(ctx)
    _save_step(task_id, "depreciation-drafted", s)

    s, artifact = _step_tb(ctx)
    _save_step(task_id, "tb-drafted", s)

    _save_step(task_id, "awaiting-signoff", {
        "ts": time.time(),
        "artifact_path": str(artifact),
        "message": f"Month-end close for {ctx.closing_month} ready for CoS sign-off.",
    })

    return CloseResult(
        task_id=task_id,
        status="awaiting_signoff",
        artifact_path=artifact,
        entries_posted=0,
        errors=errors,
        escalations=escalations,
    )


def run_post_step(task_id: str, ctx: CloseContext) -> CloseResult:
    """Step 8. Called by daemon when CoS has signed off (signal via outbox)."""
    s, posted_count, post_errors = _step_post(ctx)
    _save_step(task_id, "posted", s)
    _complete(task_id)
    return CloseResult(
        task_id=task_id,
        status="complete" if not post_errors else "failed",
        entries_posted=posted_count,
        errors=post_errors,
    )
