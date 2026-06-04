"""Tests for Bookie's Claude-driven brain. The Claude call is injected (no
network, no CLI) so we test prompt-building and answer-parsing deterministically."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.brain import categorize, _build_prompt, Proposal

ACCOUNTS = [
    {"name": "Repairs & maintenance", "type": "Expense"},
    {"name": "Contract labor", "type": "Expense"},
    {"name": "Ask My Accountant", "type": "Expense"},
]


def _runner_returning(payload):
    def run(prompt, timeout):
        return payload
    return run


def test_parses_clean_json():
    tx = {"date": "2025-08-31", "name": "Hardware Store", "memo": "job site", "amount": "1617.57"}
    p = categorize(tx, ACCOUNTS, runner=_runner_returning(
        '{"account": "Repairs & maintenance", "confidence": 0.9, "rationale": "building materials for a job site"}'))
    assert p.account == "Repairs & maintenance"
    assert p.confidence == 0.9
    assert "materials" in p.rationale


def test_extracts_json_from_surrounding_text():
    p = categorize({"name": "x"}, ACCOUNTS, runner=_runner_returning(
        'Here is my answer:\n{"account": "Contract labor", "confidence": 0.7, "rationale": "payment to a contractor"}\nThanks!'))
    assert p.account == "Contract labor"
    assert p.confidence == 0.7


def test_garbage_output_is_safe():
    p = categorize({"name": "x"}, ACCOUNTS, runner=_runner_returning("I could not decide."))
    assert p.account == ""
    assert p.confidence == 0.0
    assert p.rationale  # never empty


def test_confidence_clamped():
    p = categorize({"name": "x"}, ACCOUNTS, runner=_runner_returning(
        '{"account": "Ask My Accountant", "confidence": 5, "rationale": "x"}'))
    assert p.confidence == 1.0


def test_prompt_includes_accounts_and_transaction():
    prompt = _build_prompt({"name": "Hardware Store", "amount": "100"}, ACCOUNTS, [])
    assert "Repairs & maintenance" in prompt
    assert "Hardware Store" in prompt
    assert "JSON" in prompt


def test_prompt_includes_corrections():
    prompt = _build_prompt({"name": "Acme Supply"}, ACCOUNTS,
                           [{"vendor": "Acme Supply", "account": "Repairs & maintenance"}])
    assert "learn from these" in prompt.lower()
    assert "Acme Supply" in prompt


def test_prompt_includes_business_context():
    prompt = _build_prompt({"name": "x"}, ACCOUNTS, [], business="a coffee roaster in Portland")
    assert "a coffee roaster in Portland" in prompt


def test_batch_parses_array_and_orders():
    from bookie.brain import categorize_batch
    txns = [{"name": "Hardware Store"}, {"name": "Acme Supply"}]
    runner = lambda prompt, timeout: '[{"i":1,"account":"Repairs & maintenance","confidence":0.6,"rationale":"supplier upkeep"},{"i":0,"account":"Repairs & maintenance","confidence":0.85,"rationale":"materials"}]'
    out = categorize_batch(txns, ACCOUNTS, runner=runner)
    assert len(out) == 2
    assert out[0].confidence == 0.85   # ordered by index, not response order
    assert out[1].rationale == "supplier upkeep"
