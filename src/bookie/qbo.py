"""QuickBooks Online integration. Stub for v1.

Per Bookie PRD §7: REST v3 + OAuth 2.0. SDK: python-quickbooks + intuit-oauth.
Idempotency via Request-Id header; concurrency via SyncToken.

V1 ships interface + dry-run mode only. Live QBO sandbox wiring in Phase 2.
"""
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class QBOConfig:
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    realm_id: str = ""                # QBO company id
    environment: str = "sandbox"      # "sandbox" | "production"
    dry_run: bool = True              # default DRY-RUN — never set False without explicit CoS approval


@dataclass
class QBOResult:
    ok: bool
    request_id: str
    payload: dict
    response: dict | None = None
    error: str | None = None


def _new_request_id() -> str:
    return uuid.uuid4().hex


def post_journal_entry(
    cfg: QBOConfig,
    entry: dict,
    *,
    dry_run_dir: Path | None = None,
) -> QBOResult:
    """Post one journal entry. In dry-run, write the planned mutation as JSON to disk
    without executing. In live mode (Phase 2), call QBO REST v3 with Request-Id.
    """
    request_id = _new_request_id()
    if cfg.dry_run:
        # Persist the planned mutation for inspection
        if dry_run_dir is not None:
            dry_run_dir.mkdir(parents=True, exist_ok=True)
            (dry_run_dir / f"{request_id}.json").write_text(json.dumps({
                "request_id": request_id,
                "entry": entry,
                "mode": "dry_run",
            }, indent=2))
        return QBOResult(ok=True, request_id=request_id, payload=entry, response={"dry_run": True})
    # Live mode — not implemented in v1
    return QBOResult(
        ok=False,
        request_id=request_id,
        payload=entry,
        error="Live QBO mode not implemented in v1 (Phase 2). Set dry_run=True.",
    )


def fetch_memorized_transactions(cfg: QBOConfig) -> list[dict]:
    """Pull QBO Memorized Transactions for use in the categorization chain.

    V1 stub returns []. Phase 2 implements the live fetch.
    """
    return []
