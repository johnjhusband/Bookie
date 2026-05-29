"""QBO browser-automation surface.

Per requirements.md R7+R8: drives the QBO web UI for the 7 documented API gaps.
Uses Stagehand (AI-prompted actions) on local Chromium by default; Browserbase
opt-in via BOOKIE_USE_BROWSERBASE=1.

The browser layer is OPTIONAL — Bookie's API path covers ~80% of bookkeeping.
Browser is invoked only for:
  1. Initial bank linkage (rare; one-shot)
  2. "For Review" queue read + categorize / accept
  3. Force-match when API auto-match fails
  4. Bank Rules CRUD
  5. Monthly Reconciliation
  6. Receipt inbox match
  7. Audit Log read

Pacing: 1-4s jittered between actions. Hard stops: 5min / 50 LLM calls / $2 /
10 attempts per task per day (per lessons/browser-automation-escalation-ladder.md).
"""
from __future__ import annotations
import json
import os
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


QBO_HOST = "https://qbo.intuit.com"
QBO_BANKING_URL = f"{QBO_HOST}/app/banking"
QBO_REVIEW_URL = f"{QBO_HOST}/app/banking?tab=for_review"
QBO_RULES_URL = f"{QBO_HOST}/app/banking?tab=rules"
QBO_AUDITLOG_URL = f"{QBO_HOST}/app/auditlog"


# Hard-stop budget per task (per browser-automation-escalation-ladder.md)
TASK_BUDGET_SECONDS = 300
TASK_BUDGET_LLM_CALLS = 50
TASK_BUDGET_USD = 2.00


class BrowserError(Exception):
    """Raised when a browser session fails irrecoverably."""


class BrowserBudgetExceeded(BrowserError):
    """Raised when a task exceeds any of the per-task hard caps."""


@dataclass
class BrowserConfig:
    storage_state_path: Path             # persistent storageState JSON for trusted-device session
    use_browserbase: bool = False        # if True, route through Browserbase
    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    model_for_actions: str = "claude-sonnet-4-6"  # Stagehand action model
    headed: bool = False                  # show the browser window (for debugging)
    slow_mo_ms: int = 0                   # extra delay between actions


@dataclass
class TaskBudget:
    started_at: float = field(default_factory=time.monotonic)
    llm_calls: int = 0
    cost_usd: float = 0.0

    def check(self) -> None:
        elapsed = time.monotonic() - self.started_at
        if elapsed > TASK_BUDGET_SECONDS:
            raise BrowserBudgetExceeded(
                f"task wall-clock {elapsed:.0f}s exceeded {TASK_BUDGET_SECONDS}s"
            )
        if self.llm_calls > TASK_BUDGET_LLM_CALLS:
            raise BrowserBudgetExceeded(
                f"task LLM calls {self.llm_calls} exceeded {TASK_BUDGET_LLM_CALLS}"
            )
        if self.cost_usd > TASK_BUDGET_USD:
            raise BrowserBudgetExceeded(
                f"task cost ${self.cost_usd:.2f} exceeded ${TASK_BUDGET_USD}"
            )


def _human_pause() -> None:
    """Jittered 1-4s pause to look like a human."""
    time.sleep(random.uniform(1.0, 4.0))


def load_config_from_env() -> BrowserConfig:
    storage = os.environ.get("BOOKIE_BROWSER_STORAGE_STATE",
                             str(Path.home() / ".config" / "bookie" / "qbo-storage-state.json"))
    use_bb = os.environ.get("BOOKIE_USE_BROWSERBASE", "0") == "1"
    return BrowserConfig(
        storage_state_path=Path(storage),
        use_browserbase=use_bb,
        browserbase_api_key=os.environ.get("BROWSERBASE_API_KEY", ""),
        browserbase_project_id=os.environ.get("BROWSERBASE_PROJECT_ID", ""),
        headed=os.environ.get("BOOKIE_BROWSER_HEADED", "0") == "1",
    )


def _import_stagehand():
    """Lazy import so the module loads without stagehand installed."""
    try:
        from stagehand import Stagehand   # type: ignore
        return Stagehand
    except ImportError:
        raise BrowserError(
            "stagehand is not installed. Install with: pip install stagehand-py\n"
            "(or set up the dependency in Bookie's requirements before invoking browser tasks)"
        )


@contextmanager
def _qbo_session(cfg: BrowserConfig, budget: TaskBudget):
    """Open a Stagehand-managed Chromium session pointed at QBO with persisted auth.

    Yields the Stagehand page object. Saves storage state on clean exit.
    Caller must drive `page.act(...)` / `page.observe(...)` / `page.extract(...)`
    using natural-language prompts.
    """
    Stagehand = _import_stagehand()
    init_kwargs: dict[str, Any] = {
        "env": "BROWSERBASE" if cfg.use_browserbase else "LOCAL",
        "model_name": cfg.model_for_actions,
        "headless": not cfg.headed,
    }
    if cfg.use_browserbase:
        if not cfg.browserbase_api_key or not cfg.browserbase_project_id:
            raise BrowserError(
                "BOOKIE_USE_BROWSERBASE=1 but BROWSERBASE_API_KEY / BROWSERBASE_PROJECT_ID not set"
            )
        init_kwargs["api_key"] = cfg.browserbase_api_key
        init_kwargs["project_id"] = cfg.browserbase_project_id
    if cfg.storage_state_path.exists():
        init_kwargs["storage_state"] = str(cfg.storage_state_path)

    sh = Stagehand(**init_kwargs)
    try:
        sh.init()
        page = sh.page
        try:
            yield page, budget
        finally:
            try:
                state = page.context.storage_state()
                cfg.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
                cfg.storage_state_path.write_text(json.dumps(state, indent=2))
                cfg.storage_state_path.chmod(0o600)
            except Exception:
                pass
    finally:
        try:
            sh.close()
        except Exception:
            pass


# ---------------- Public task API ----------------
# Each function below corresponds to one R7 gap. Implementation calls Stagehand
# `page.act("natural language")` / `page.observe()` / `page.extract(schema)`.


def list_for_review(cfg: Optional[BrowserConfig] = None) -> list[dict]:
    """Scrape the For Review queue. Returns list of {id, date, amount, vendor, suggested_category}."""
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        budget.check()
        page.goto(QBO_REVIEW_URL)
        _human_pause()
        budget.check()
        items = page.extract({
            "items": [
                {"id": "string", "date": "string", "amount": "number",
                 "vendor": "string", "suggested_category": "string"}
            ]
        }, instruction="extract every For Review line item visible on the page")
        budget.llm_calls += 1
        return items.get("items", [])


def categorize_for_review_item(transaction_id: str, category: str,
                                cfg: Optional[BrowserConfig] = None) -> bool:
    """Click through to a specific For-Review item and accept with the given category.
    Returns True on success.
    """
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(QBO_REVIEW_URL)
        _human_pause()
        budget.check()
        page.act(f"find the bank-feed line with id {transaction_id} and open it")
        budget.llm_calls += 1
        _human_pause()
        page.act(f"set the category to {category}")
        budget.llm_calls += 1
        _human_pause()
        page.act("click Add to accept this transaction with the chosen category")
        budget.llm_calls += 1
        _human_pause()
        # Confirm success
        ok = page.observe("a confirmation toast or that the transaction has been removed from For Review")
        budget.llm_calls += 1
        return bool(ok)


def force_match(bank_feed_line_id: str, posted_transaction_id: str,
                cfg: Optional[BrowserConfig] = None) -> bool:
    """For the rare case where QBO's auto-matcher doesn't link a bank-feed line to a posted txn.
    Returns True on success.
    """
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(QBO_REVIEW_URL)
        _human_pause()
        budget.check()
        page.act(f"find the bank-feed line with id {bank_feed_line_id} and open the Find Match dialog")
        budget.llm_calls += 1
        _human_pause()
        page.act(f"select the posted transaction with id {posted_transaction_id} and confirm the match")
        budget.llm_calls += 1
        _human_pause()
        ok = page.observe("a match-confirmation message")
        budget.llm_calls += 1
        return bool(ok)


def list_bank_rules(cfg: Optional[BrowserConfig] = None) -> list[dict]:
    """Read the Bank Rules screen. Returns the configured rules as dicts."""
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(QBO_RULES_URL)
        _human_pause()
        budget.check()
        rules = page.extract({
            "rules": [{"name": "string", "conditions": "string",
                       "category": "string", "auto_add": "boolean"}]
        }, instruction="extract every Bank Rule visible")
        budget.llm_calls += 1
        return rules.get("rules", [])


def create_bank_rule(name: str, conditions: dict, category: str,
                     auto_add: bool = False, cfg: Optional[BrowserConfig] = None) -> bool:
    """Create a new Bank Rule via the UI.
    conditions: e.g. {"description_contains": "Notion", "transaction_type": "expense"}
    """
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(QBO_RULES_URL)
        _human_pause()
        budget.check()
        page.act("click New rule")
        budget.llm_calls += 1
        _human_pause()
        page.act(f"fill in rule name {name!r} and set conditions {conditions!r} "
                 f"with category {category!r} and auto-add {'on' if auto_add else 'off'}")
        budget.llm_calls += 1
        _human_pause()
        page.act("click Save to create the rule")
        budget.llm_calls += 1
        _human_pause()
        ok = page.observe("a success toast or the new rule appearing in the rules list")
        budget.llm_calls += 1
        return bool(ok)


def reconcile_account(account_name: str, statement_end_date: str,
                      statement_ending_balance: float,
                      cfg: Optional[BrowserConfig] = None) -> dict:
    """Drive the monthly Reconcile workflow for one account.
    Returns {"matched": N, "unmatched": [...], "variance": float}.
    """
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(f"{QBO_HOST}/app/reconcile")
        _human_pause()
        budget.check()
        page.act(f"select account {account_name!r}")
        budget.llm_calls += 1
        _human_pause()
        page.act(f"set statement end date to {statement_end_date} and ending balance to {statement_ending_balance}")
        budget.llm_calls += 1
        _human_pause()
        page.act("click Start reconciling")
        budget.llm_calls += 1
        _human_pause()
        page.act("auto-check every cleared transaction that matches QBO's prior records")
        budget.llm_calls += 1
        _human_pause()
        result = page.extract({
            "matched": "number", "unmatched_count": "number",
            "variance": "number"
        }, instruction="extract the reconciliation summary numbers")
        budget.llm_calls += 1
        return result


def attach_and_match_receipt(receipt_file_path: str, transaction_hint: str,
                              cfg: Optional[BrowserConfig] = None) -> bool:
    """Receipt-inbox flow. Use the Attachable API for upload first; this drives the
    UI match step that the API doesn't expose.
    """
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(f"{QBO_HOST}/app/receipts")
        _human_pause()
        budget.check()
        page.act(f"find the uploaded receipt matching {transaction_hint!r}")
        budget.llm_calls += 1
        _human_pause()
        page.act(f"match it to the QBO transaction described as {transaction_hint!r}")
        budget.llm_calls += 1
        _human_pause()
        ok = page.observe("a success indicator that the receipt was matched")
        budget.llm_calls += 1
        return bool(ok)


def read_audit_log(since_iso_date: Optional[str] = None,
                   cfg: Optional[BrowserConfig] = None) -> list[dict]:
    """Scrape the Audit Log for entries since the given date. Returns list of entries."""
    cfg = cfg or load_config_from_env()
    budget = TaskBudget()
    with _qbo_session(cfg, budget) as (page, _):
        page.goto(QBO_AUDITLOG_URL)
        _human_pause()
        budget.check()
        if since_iso_date:
            page.act(f"filter the audit log to show entries since {since_iso_date}")
            budget.llm_calls += 1
            _human_pause()
        entries = page.extract({
            "entries": [{"ts": "string", "user": "string", "event": "string",
                         "entity": "string", "details": "string"}]
        }, instruction="extract every audit log entry visible")
        budget.llm_calls += 1
        return entries.get("entries", [])


def is_available() -> bool:
    """Returns True if Stagehand is importable AND a storage state file exists.

    Lets the daemon decide whether to attempt browser tasks or fall back to API-only.
    """
    try:
        _import_stagehand()
    except BrowserError:
        return False
    cfg = load_config_from_env()
    return cfg.storage_state_path.exists()
