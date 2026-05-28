"""Plaid bank-feed integration. Live Transactions API + Link.

Credentials live in `config/plaid-credentials.json` (gitignored). Required keys:
  client_id, secret, environment ("sandbox" | "development" | "production")

Per-bank access_tokens are stored in `config/plaid-items.json`:
  {
    "items": [
      {"institution_name": "Chase", "access_token": "...", "cursor": "..."}
    ]
  }

The transactions/sync endpoint uses cursor-based pagination — we persist the
cursor between runs so each tick only pulls deltas.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import urllib.request
import urllib.error
import urllib.parse

from bookie.models import Transaction


PLAID_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidError(Exception):
    """Raised on any Plaid API failure that isn't auto-recoverable."""


@dataclass
class PlaidConfig:
    client_id: str
    secret: str
    environment: str = "sandbox"

    @property
    def host(self) -> str:
        return PLAID_HOSTS[self.environment]


@dataclass
class PlaidItem:
    institution_name: str
    access_token: str
    cursor: str = ""


def load_config(path: str | Path) -> PlaidConfig:
    p = Path(path)
    if not p.exists():
        raise PlaidError(f"Plaid credentials file not found: {p}")
    with p.open() as f:
        d = json.load(f)
    return PlaidConfig(
        client_id=d["client_id"],
        secret=d["secret"],
        environment=d.get("environment", "sandbox"),
    )


def load_items(path: str | Path) -> list[PlaidItem]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open() as f:
        d = json.load(f)
    return [PlaidItem(
        institution_name=i["institution_name"],
        access_token=i["access_token"],
        cursor=i.get("cursor", ""),
    ) for i in d.get("items", [])]


def save_items(items: list[PlaidItem], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "items": [{
            "institution_name": i.institution_name,
            "access_token": i.access_token,
            "cursor": i.cursor,
        } for i in items],
    }, indent=2))
    p.chmod(0o600)


def _api_call(cfg: PlaidConfig, endpoint: str, body: dict) -> dict:
    body = {**body, "client_id": cfg.client_id, "secret": cfg.secret}
    req = urllib.request.Request(
        f"{cfg.host}{endpoint}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise PlaidError(f"Plaid {endpoint} failed HTTP {e.code}: "
                         f"{e.read().decode()[:500]}") from e


def create_link_token(cfg: PlaidConfig, *, user_id: str = "bookie",
                      client_name: str = "Bookie") -> str:
    """Returns a one-time link_token for the Plaid Link OAuth flow."""
    resp = _api_call(cfg, "/link/token/create", {
        "user": {"client_user_id": user_id},
        "client_name": client_name,
        "products": ["transactions"],
        "country_codes": ["US"],
        "language": "en",
    })
    return resp["link_token"]


def exchange_public_token(cfg: PlaidConfig, public_token: str) -> str:
    """Exchange the public_token from Plaid Link for a permanent access_token."""
    resp = _api_call(cfg, "/item/public_token/exchange", {
        "public_token": public_token,
    })
    return resp["access_token"]


def fetch_transactions(cfg: PlaidConfig, item: PlaidItem) -> tuple[list[Transaction], PlaidItem]:
    """Pull all new/modified/removed transactions since the last cursor.

    Returns (transactions, updated_item_with_new_cursor).
    """
    added_all = []
    modified_all = []
    removed_all = []
    cursor = item.cursor
    has_more = True
    while has_more:
        body = {"access_token": item.access_token}
        if cursor:
            body["cursor"] = cursor
        resp = _api_call(cfg, "/transactions/sync", body)
        added_all.extend(resp.get("added", []))
        modified_all.extend(resp.get("modified", []))
        removed_all.extend(resp.get("removed", []))
        cursor = resp.get("next_cursor", cursor)
        has_more = resp.get("has_more", False)

    transactions = []
    for t in (added_all + modified_all):
        transactions.append(Transaction(
            id=t["transaction_id"],
            date=date.fromisoformat(t["date"]),
            # Plaid amounts are positive for outflows, negative for inflows; flip to our convention
            amount=-float(t["amount"]),
            vendor=(t.get("merchant_name") or t.get("name") or "").strip(),
            memo=t.get("name", "")[:200],
            account=t.get("account_id", ""),
            raw=t,
        ))
    updated = PlaidItem(
        institution_name=item.institution_name,
        access_token=item.access_token,
        cursor=cursor,
    )
    return transactions, updated


def fetch_transactions_from_file(path: Path) -> list[Transaction]:
    """Mock source for testing without live Plaid: load transactions from JSON file."""
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
