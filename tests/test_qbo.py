"""Tests for the QBO reclassify mechanics, against MOCKED responses (no live API).

Covers the rules verified against current Intuit docs:
- the full Line array must be sent (sparse merge does not apply to Line)
- one line's AccountRef is swapped, others preserved
- the 5010 stale-token error triggers a re-read + retry
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.qbo import (build_purchase_reclassify_body, reclassify_purchase,
                        QBOConfig, QBOError)


PURCHASE = {
    "Id": "252", "SyncToken": "0", "PaymentType": "Cash",
    "AccountRef": {"value": "35", "name": "Checking"},
    "Line": [
        {"Id": "1", "Amount": 100.0, "DetailType": "AccountBasedExpenseLineDetail",
         "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "7", "name": "Office Supplies"}}},
        {"Id": "2", "Amount": 50.0, "DetailType": "AccountBasedExpenseLineDetail",
         "AccountBasedExpenseLineDetail": {"AccountRef": {"value": "7", "name": "Office Supplies"}}},
    ],
}


def test_body_swaps_only_target_line():
    body = build_purchase_reclassify_body(PURCHASE, line_id="1",
                                          new_account_id="63", new_account_name="Advertising")
    assert body["sparse"] is True
    assert body["Id"] == "252"
    assert body["SyncToken"] == "0"
    # both lines present (full array required)
    assert len(body["Line"]) == 2
    # line 1 reclassified
    assert body["Line"][0]["AccountBasedExpenseLineDetail"]["AccountRef"]["value"] == "63"
    # line 2 untouched
    assert body["Line"][1]["AccountBasedExpenseLineDetail"]["AccountRef"]["value"] == "7"


def test_body_preserves_full_line_array():
    # the #1 gotcha: sending a partial Line array deletes lines. We always send all.
    body = build_purchase_reclassify_body(PURCHASE, line_id="2",
                                          new_account_id="91")
    ids = [l["Id"] for l in body["Line"]]
    assert ids == ["1", "2"]


def test_does_not_mutate_input():
    build_purchase_reclassify_body(PURCHASE, line_id="1", new_account_id="63")
    # original untouched
    assert PURCHASE["Line"][0]["AccountBasedExpenseLineDetail"]["AccountRef"]["value"] == "7"


def _cfg():
    return QBOConfig(client_id="x", client_secret="y", refresh_token="z", realm_id="1")


def test_reclassify_success_with_mock():
    calls = []
    def fake_api(method, path, **kw):
        calls.append((method, path, kw))
        if method == "GET":
            return {"Purchase": PURCHASE}
        return {"Purchase": {**PURCHASE, "SyncToken": "1"}}
    result = reclassify_purchase(_cfg(), Path("/tmp/x"), purchase_id="252",
                                 line_id="1", new_account_id="63", _api=fake_api)
    assert result.ok is True
    # read then update
    assert calls[0][0] == "GET"
    assert calls[1][0] == "POST"


def test_reclassify_retries_on_stale_token():
    state = {"posts": 0}
    def fake_api(method, path, **kw):
        if method == "GET":
            return {"Purchase": PURCHASE}
        state["posts"] += 1
        if state["posts"] == 1:
            raise QBOError("HTTP 400: ValidationFault code 5010 Stale Object Error")
        return {"Purchase": {**PURCHASE, "SyncToken": "2"}}
    result = reclassify_purchase(_cfg(), Path("/tmp/x"), purchase_id="252",
                                 line_id="1", new_account_id="63", _api=fake_api)
    assert result.ok is True
    assert state["posts"] == 2  # first failed (stale), second succeeded after re-read


def test_reclassify_gives_up_after_retries():
    def fake_api(method, path, **kw):
        if method == "GET":
            return {"Purchase": PURCHASE}
        raise QBOError("HTTP 400: code 5010 Stale Object Error")
    result = reclassify_purchase(_cfg(), Path("/tmp/x"), purchase_id="252",
                                 line_id="1", new_account_id="63", _api=fake_api,
                                 max_retries=2)
    assert result.ok is False
    assert "stale" in result.error.lower()


def test_reclassify_non_stale_error_does_not_retry():
    state = {"posts": 0}
    def fake_api(method, path, **kw):
        if method == "GET":
            return {"Purchase": PURCHASE}
        state["posts"] += 1
        raise QBOError("HTTP 400: some other validation error")
    result = reclassify_purchase(_cfg(), Path("/tmp/x"), purchase_id="252",
                                 line_id="1", new_account_id="63", _api=fake_api)
    assert result.ok is False
    assert state["posts"] == 1  # did not retry on non-stale error
