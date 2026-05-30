"""QuickBooks Online integration. Live REST v3 + OAuth 2.0.

Credentials live in `config/qbo-credentials.json` (gitignored). Required keys:
  client_id, client_secret, refresh_token, realm_id, environment

The refresh_token mints short-lived access_tokens; we auto-refresh on 401.
Every mutation uses a Request-Id header for idempotency and SyncToken for
optimistic concurrency.
"""
from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import urllib.request
import urllib.error
import urllib.parse
import base64


INTUIT_OAUTH_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
INTUIT_API_BASE_SANDBOX = "https://sandbox-quickbooks.api.intuit.com"
INTUIT_API_BASE_PROD = "https://quickbooks.api.intuit.com"


class QBOError(Exception):
    """Raised on any QBO API failure that isn't auto-recoverable."""


@dataclass
class QBOConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    realm_id: str
    environment: str = "sandbox"
    access_token: str = ""
    access_token_expires_at: float = 0.0
    # Refresh tokens are capped at 5 years (Intuit Nov 2025 policy). When this
    # is set, daemon can warn / trigger Reconnect URL flow before expiry.
    refresh_token_expires_at: float = 0.0

    @property
    def api_base(self) -> str:
        return INTUIT_API_BASE_PROD if self.environment == "production" else INTUIT_API_BASE_SANDBOX


@dataclass
class QBOResult:
    ok: bool
    request_id: str
    payload: dict
    response: dict | None = None
    error: str | None = None
    http_status: int | None = None


def _new_request_id() -> str:
    return uuid.uuid4().hex


def load_config(path: str | Path) -> QBOConfig:
    """Load QBO credentials from a JSON file."""
    p = Path(path)
    if not p.exists():
        raise QBOError(f"QBO credentials file not found: {p}. "
                       f"Run `bookie qbo-setup` to authorize, or populate manually.")
    with p.open() as f:
        d = json.load(f)
    for required in ("client_id", "client_secret", "refresh_token", "realm_id"):
        if not d.get(required):
            raise QBOError(f"QBO credentials missing required field: {required}")
    return QBOConfig(
        client_id=d["client_id"],
        client_secret=d["client_secret"],
        refresh_token=d["refresh_token"],
        realm_id=d["realm_id"],
        environment=d.get("environment", "sandbox"),
        access_token=d.get("access_token", ""),
        access_token_expires_at=float(d.get("access_token_expires_at", 0.0)),
        refresh_token_expires_at=float(d.get("refresh_token_expires_at", 0.0)),
    )


def save_config(cfg: QBOConfig, path: str | Path) -> None:
    """Persist the (possibly refreshed) credentials back to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "refresh_token": cfg.refresh_token,
        "realm_id": cfg.realm_id,
        "environment": cfg.environment,
        "access_token": cfg.access_token,
        "access_token_expires_at": cfg.access_token_expires_at,
        "refresh_token_expires_at": cfg.refresh_token_expires_at,
    }, indent=2))
    p.chmod(0o600)


def refresh_access_token(cfg: QBOConfig) -> QBOConfig:
    """Exchange the refresh_token for a new access_token. Also rotates refresh_token."""
    creds = f"{cfg.client_id}:{cfg.client_secret}".encode()
    auth_header = base64.b64encode(creds).decode()
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": cfg.refresh_token,
    }).encode()
    req = urllib.request.Request(
        INTUIT_OAUTH_TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise QBOError(f"OAuth refresh failed HTTP {e.code}: {e.read().decode()[:300]}") from e
    now = time.time()
    cfg.access_token = data["access_token"]
    cfg.access_token_expires_at = now + int(data.get("expires_in", 3600)) - 60
    # Refresh token rotates roughly every 24h; persist the new one immediately
    # or we silently lose access on the next refresh.
    if "refresh_token" in data:
        cfg.refresh_token = data["refresh_token"]
    if "x_refresh_token_expires_in" in data:
        cfg.refresh_token_expires_at = now + int(data["x_refresh_token_expires_in"])
    return cfg


def _ensure_access_token(cfg: QBOConfig, creds_path: Path) -> QBOConfig:
    if not cfg.access_token or time.time() >= cfg.access_token_expires_at:
        cfg = refresh_access_token(cfg)
        save_config(cfg, creds_path)
    return cfg


def _api_call(cfg: QBOConfig, creds_path: Path, method: str, path: str,
              *, body: dict | None = None, params: dict | None = None,
              request_id: str | None = None) -> dict:
    """One QBO REST call. Auto-refreshes on 401. Raises QBOError on terminal failure."""
    cfg = _ensure_access_token(cfg, creds_path)
    url = f"{cfg.api_base}/v3/company/{cfg.realm_id}{path}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    rid = request_id or _new_request_id()
    headers = {
        "Authorization": f"Bearer {cfg.access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Request-Id": rid,
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Force refresh and retry once
            cfg.access_token = ""
            cfg = _ensure_access_token(cfg, creds_path)
            headers["Authorization"] = f"Bearer {cfg.access_token}"
            req2 = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req2, timeout=60) as r:
                    return json.loads(r.read().decode() or "{}")
            except urllib.error.HTTPError as e2:
                raise QBOError(f"QBO {method} {path} failed after refresh: HTTP {e2.code}: "
                               f"{e2.read().decode()[:500]}") from e2
        raise QBOError(f"QBO {method} {path} failed: HTTP {e.code}: "
                       f"{e.read().decode()[:500]}") from e


def post_journal_entry(cfg: QBOConfig, creds_path: Path, entry: dict,
                       *, request_id: str | None = None) -> QBOResult:
    """Post one journal entry. Idempotent via Request-Id."""
    rid = request_id or _new_request_id()
    try:
        resp = _api_call(cfg, creds_path, "POST", "/journalentry",
                          body=entry, request_id=rid)
    except QBOError as e:
        return QBOResult(ok=False, request_id=rid, payload=entry, error=str(e))
    return QBOResult(ok=True, request_id=rid, payload=entry, response=resp)


def fetch_chart_of_accounts(cfg: QBOConfig, creds_path: Path) -> list[dict]:
    """Pull the locked CoA. Returns list of {name, id, type, fully_qualified_name}."""
    resp = _api_call(cfg, creds_path, "GET", "/query",
                     params={"query": "select * from Account"})
    items = resp.get("QueryResponse", {}).get("Account", [])
    return [{
        "id": a.get("Id"),
        "name": a.get("Name"),
        "type": a.get("AccountType"),
        "fully_qualified_name": a.get("FullyQualifiedName"),
        "active": a.get("Active", True),
    } for a in items]


def fetch_memorized_transactions(cfg: QBOConfig, creds_path: Path) -> list[dict]:
    """Pull QBO Memorized Transactions for the categorizer's step-1 rules."""
    # QBO uses RecurringTransaction in v3 API for the memorized-pattern equivalent
    try:
        resp = _api_call(cfg, creds_path, "GET", "/query",
                         params={"query": "select * from RecurringTransaction"})
    except QBOError:
        return []
    items = resp.get("QueryResponse", {}).get("RecurringTransaction", [])
    return [{
        "id": r.get("Id"),
        "name": r.get("Name"),
        "raw": r,
    } for r in items]


def fetch_vendors(cfg: QBOConfig, creds_path: Path) -> list[dict]:
    resp = _api_call(cfg, creds_path, "GET", "/query",
                     params={"query": "select * from Vendor"})
    items = resp.get("QueryResponse", {}).get("Vendor", [])
    return [{
        "id": v.get("Id"),
        "display_name": v.get("DisplayName"),
        "primary_email": (v.get("PrimaryEmailAddr") or {}).get("Address"),
        "tax_identifier": v.get("TaxIdentifier"),
        "active": v.get("Active", True),
    } for v in items]


def build_purchase_reclassify_body(purchase: dict, *, line_id: str,
                                   new_account_id: str,
                                   new_account_name: str = "") -> dict:
    """Pure function: given a fetched Purchase entity, build the sparse-update body
    that reclassifies one expense line to a new account.

    CRITICAL (per Intuit): the Line array is NOT sparse-merged — we must send
    the FULL Line array (every line with its Id), or omitted lines get deleted.
    We copy all lines and swap AccountRef only on the target line.
    """
    lines_out = []
    for line in purchase.get("Line", []):
        new_line = dict(line)  # shallow copy
        if str(line.get("Id")) == str(line_id):
            detail = dict(line.get("AccountBasedExpenseLineDetail", {}))
            ref = dict(detail.get("AccountRef", {}))
            ref["value"] = new_account_id
            if new_account_name:
                ref["name"] = new_account_name
            detail["AccountRef"] = ref
            new_line["AccountBasedExpenseLineDetail"] = detail
        lines_out.append(new_line)
    return {
        "sparse": True,
        "Id": purchase["Id"],
        "SyncToken": purchase["SyncToken"],
        "Line": lines_out,
    }


def reclassify_purchase(cfg: QBOConfig, creds_path: Path, *, purchase_id: str,
                        line_id: str, new_account_id: str,
                        new_account_name: str = "",
                        _api=None, max_retries: int = 2) -> QBOResult:
    """Read a Purchase, swap one line's expense account, sparse-update it.

    Handles the 5010 stale-object error by re-reading and re-applying. `_api`
    is injectable for testing (defaults to the live _api_call).
    """
    api = _api or (lambda method, path, **kw: _api_call(cfg, creds_path, method, path, **kw))
    rid = _new_request_id()
    attempt = 0
    last_error = None
    while attempt <= max_retries:
        attempt += 1
        # 1. Read current entity for fresh SyncToken
        try:
            read = api("GET", f"/purchase/{purchase_id}")
        except QBOError as e:
            return QBOResult(ok=False, request_id=rid, payload={}, error=f"read failed: {e}")
        purchase = read.get("Purchase") or read.get("QueryResponse", {}).get("Purchase", [{}])[0]
        if not purchase:
            return QBOResult(ok=False, request_id=rid, payload={}, error="purchase not found")
        body = build_purchase_reclassify_body(
            purchase, line_id=line_id, new_account_id=new_account_id,
            new_account_name=new_account_name)
        # 2. Update
        try:
            resp = api("POST", "/purchase", body=body, request_id=rid)
            return QBOResult(ok=True, request_id=rid, payload=body, response=resp)
        except QBOError as e:
            msg = str(e)
            last_error = msg
            # 5010 stale object → re-read and retry
            if "5010" in msg or "Stale" in msg:
                continue
            return QBOResult(ok=False, request_id=rid, payload=body, error=msg)
    return QBOResult(ok=False, request_id=rid, payload={}, error=f"stale-token retries exhausted: {last_error}")


def update_entity(cfg: QBOConfig, creds_path: Path, entity_type: str,
                  entity: dict, *, request_id: str | None = None) -> QBOResult:
    """Update with SyncToken for optimistic concurrency. `entity` must include Id and SyncToken."""
    if "SyncToken" not in entity:
        return QBOResult(ok=False, request_id=request_id or _new_request_id(),
                         payload=entity, error="entity missing SyncToken")
    rid = request_id or _new_request_id()
    try:
        resp = _api_call(cfg, creds_path, "POST", f"/{entity_type.lower()}",
                         body=entity, request_id=rid)
    except QBOError as e:
        return QBOResult(ok=False, request_id=rid, payload=entity, error=str(e))
    return QBOResult(ok=True, request_id=rid, payload=entity, response=resp)
