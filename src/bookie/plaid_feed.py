"""Plaid bank-feed integration. Stub for v1.

Per Bookie PRD §7: Plaid OAuth-only (~90% of US major banks support OAuth).
No password storage. SOC 2 + ISO 27001 vendor.

V1 ships the interface + a JSON-file mock source so the categorizer can
be exercised end-to-end without live Plaid credentials.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from bookie.models import Transaction


@dataclass
class PlaidConfig:
    client_id: str = ""
    secret: str = ""
    environment: str = "sandbox"     # "sandbox" | "development" | "production"
    access_tokens: dict[str, str] | None = None  # {institution_name: access_token}


def fetch_transactions_from_file(path: Path) -> list[Transaction]:
    """Load transactions from a JSON file (mock source for v1).

    Expected format: list of {id, date, amount, vendor, memo, account}.
    """
    data = json.loads(path.read_text())
    out = []
    for r in data:
        out.append(Transaction(
            id=r["id"],
            date=date.fromisoformat(r["date"]),
            amount=float(r["amount"]),
            vendor=r.get("vendor", ""),
            memo=r.get("memo", ""),
            account=r.get("account", ""),
            raw=r,
        ))
    return out


def fetch_transactions_live(cfg: PlaidConfig, *, start: date, end: date) -> list[Transaction]:
    """Live Plaid fetch. Not implemented in v1 (Phase 2)."""
    raise NotImplementedError("Live Plaid fetch is Phase 2. Use fetch_transactions_from_file for v1.")
