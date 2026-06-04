"""Bookie's brain — Claude reasons over each transaction. No hardcoded rules.

The judgment (what account a transaction belongs to, why) is done by Claude
running headless via the `claude` CLI on the user's existing subscription —
NO API key. Code here only builds the prompt, runs Claude, and parses the
answer. Given a transaction plus context (the real chart of accounts and any
prior corrections the owner made), Claude returns the proposed account, a
confidence, and a one-line rationale.

This file contains ZERO categorization logic of its own — that is the whole
point. Bookie is an AI employee, not a keyword script.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

CLAUDE_BIN = "claude"

# Generic fallback when no business profile is supplied. The owner's real
# business description lives OUTSIDE this repo (see README → "Tell Bookie about
# your business"); point $BOOKIE_BUSINESS_PROFILE at that file.
DEFAULT_BUSINESS = "a small business"


@dataclass
class Proposal:
    account: str
    confidence: float
    rationale: str


def claude_available() -> bool:
    """True if the Claude CLI (Bookie's brain) is present and can be run here."""
    return shutil.which(CLAUDE_BIN) is not None


def load_business_context() -> str:
    """One-line description of the business, for the prompt.

    Read from the file named in $BOOKIE_BUSINESS_PROFILE (a private, un-committed
    file describing the owner's business). Falls back to a generic description so
    the public code carries NO owner-specific facts.
    """
    path = os.environ.get("BOOKIE_BUSINESS_PROFILE")
    if path:
        try:
            text = Path(path).read_text().strip()
            if text:
                return text
        except OSError:
            pass
    return DEFAULT_BUSINESS


def _build_prompt(tx: dict, accounts: list[dict], corrections: list[dict],
                  business: str = DEFAULT_BUSINESS) -> str:
    acct_lines = "\n".join(
        f"- {a.get('name')} ({a.get('type', '')})" for a in accounts if a.get("name"))
    corr = ""
    if corrections:
        corr = "\n\nPast corrections the owner made (learn from these — they override your guess):\n" + \
            "\n".join(f"- \"{c.get('vendor', '')}\" / \"{c.get('memo', '')}\" -> {c.get('account', '')}"
                      for c in corrections)
    return f"""You are Bookie, the bookkeeper for the following business:
{business}

Categorize ONE QuickBooks transaction into exactly one account from the chart of accounts below.

Transaction:
  date: {tx.get('date', '')}
  type: {tx.get('type', '')}
  payee/name: {tx.get('name', '')}
  memo: {tx.get('memo', '')}
  amount: {tx.get('amount', '')}

Chart of accounts — choose the single best fit, returning the account NAME exactly as written:
{acct_lines}{corr}

Think about what the transaction actually is for this kind of business (e.g. a hardware store near a job site = repairs/materials; a title company or wire transfer = an asset purchase/sale or financing, not a fee; a person-to-person payment to an individual = contract labor; a payment to a credit-card company = a transfer, not an expense). If you are not reasonably sure, return a LOW confidence and pick the closest account — never guess confidently.

Respond with ONLY a JSON object and nothing else:
{{"account": "<exact account name from the list>", "confidence": <number 0.0-1.0>, "rationale": "<one short sentence>"}}"""


def _run_claude(prompt: str, timeout: int) -> str:
    """Run Claude headless and return its stdout. Uses the user's subscription."""
    out = subprocess.run([CLAUDE_BIN, "-p", prompt],
                         capture_output=True, text=True, timeout=timeout)
    return out.stdout or ""


def _to_proposal(data: dict) -> Proposal:
    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    return Proposal(
        account=str(data.get("account", "")),
        confidence=max(0.0, min(1.0, conf)),
        rationale=str(data.get("rationale", "")) or "no rationale returned",
    )


def categorize(tx: dict, accounts: list[dict],
               corrections: list[dict] | None = None, *,
               business: str | None = None,
               timeout: int = 120,
               runner: Callable[[str, int], str] | None = None) -> Proposal:
    """Ask Claude to categorize ONE transaction. `runner` is injectable for tests."""
    run = runner or _run_claude
    biz = business if business is not None else load_business_context()
    text = (run(_build_prompt(tx, accounts, corrections or [], biz), timeout) or "").strip()
    start, end = text.find("{"), text.rfind("}")
    data = {}
    if 0 <= start < end:
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            data = {}
    return _to_proposal(data)


def _build_batch_prompt(txns: list[dict], accounts: list[dict], corrections: list[dict],
                        business: str = DEFAULT_BUSINESS) -> str:
    acct_lines = "\n".join(f"- {a.get('name')} ({a.get('type','')})" for a in accounts if a.get("name"))
    corr = ""
    if corrections:
        corr = "\n\nPast owner corrections (learn from these; they override your guess):\n" + \
            "\n".join(f"- \"{c.get('vendor','')}\" -> {c.get('account','')}" for c in corrections)
    tx_lines = "\n".join(
        f'{i}. date={t.get("date","")} type={t.get("type","")} name="{t.get("name","")}" '
        f'memo="{t.get("memo","")}" amount={t.get("amount","")}'
        for i, t in enumerate(txns))
    return f"""You are Bookie, bookkeeper for the following business:
{business}

Categorize EACH transaction below into exactly one account from the chart of accounts, using the NAME exactly as written.

Reason about what each transaction really is for this business (a hardware store near a job site = repairs/materials; a title company or wire transfer = an asset purchase/sale or financing, not a fee; a person-to-person payment to an individual = contract labor; a payment to a credit-card company = a transfer, not an expense). When unsure, give LOW confidence — never guess confidently.

Chart of accounts:
{acct_lines}{corr}

Transactions:
{tx_lines}

Respond with ONLY a JSON array, one object per transaction in order:
[{{"i": <index>, "account": "<exact name>", "confidence": <0.0-1.0>, "rationale": "<one short sentence>"}}, ...]"""


def categorize_batch(txns: list[dict], accounts: list[dict],
                     corrections: list[dict] | None = None, *,
                     business: str | None = None,
                     timeout: int = 300,
                     runner: Callable[[str, int], str] | None = None) -> list[Proposal]:
    """Categorize ALL transactions in ONE Claude call (fast; Claude sees them together)."""
    if not txns:
        return []
    run = runner or _run_claude
    biz = business if business is not None else load_business_context()
    text = (run(_build_batch_prompt(txns, accounts, corrections or [], biz), timeout) or "").strip()
    start, end = text.find("["), text.rfind("]")
    rows = []
    if 0 <= start < end:
        try:
            rows = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            rows = []
    by_i = {r.get("i"): r for r in rows if isinstance(r, dict)}
    out = []
    for idx in range(len(txns)):
        out.append(_to_proposal(by_i.get(idx, {})))
    return out
