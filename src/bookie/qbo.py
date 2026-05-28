"""QuickBooks Online integration.

REST v3 + OAuth 2.0. SDK: python-quickbooks + intuit-oauth.
Idempotency via Request-Id header; concurrency via SyncToken.

Live wiring requires OAuth credentials in config/qbo.json. Stub posts raise
NotImplementedError until those are wired.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass


@dataclass
class QBOConfig:
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    realm_id: str = ""        # QBO company id


@dataclass
class QBOResult:
    ok: bool
    request_id: str
    payload: dict
    response: dict | None = None
    error: str | None = None


def _new_request_id() -> str:
    return uuid.uuid4().hex


def post_journal_entry(cfg: QBOConfig, entry: dict) -> QBOResult:
    """Post one journal entry to QBO via REST v3.

    Not wired yet. When credentials are populated in QBOConfig, this calls
    POST /v3/company/{realm_id}/journalentry with the Request-Id header.
    """
    request_id = _new_request_id()
    raise NotImplementedError(
        f"QBO live integration not wired yet. request_id={request_id}. "
        "Populate QBOConfig with OAuth credentials and implement the REST call."
    )


def fetch_memorized_transactions(cfg: QBOConfig) -> list[dict]:
    """Pull QBO Memorized Transactions for use in the categorization chain.

    Not wired yet — returns [] for now. When wired, calls
    GET /v3/company/{realm_id}/query?query=select * from PreferenceMemorizedTransaction
    (or the appropriate endpoint for memorized transactions).
    """
    return []
