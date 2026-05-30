"""Tests for the browser-automation surface — budget/hard-stop logic and
availability, against mocked Stagehand (no live browser, no network)."""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie import browser
from bookie.browser import (TaskBudget, BrowserBudgetExceeded, BrowserConfig,
                            load_config_from_env, TASK_BUDGET_LLM_CALLS,
                            TASK_BUDGET_USD, is_available)


def test_budget_passes_when_under_caps():
    b = TaskBudget()
    b.llm_calls = 1
    b.cost_usd = 0.10
    b.check()  # should not raise


def test_budget_trips_on_llm_call_cap():
    b = TaskBudget()
    b.llm_calls = TASK_BUDGET_LLM_CALLS + 1
    with pytest.raises(BrowserBudgetExceeded):
        b.check()


def test_budget_trips_on_cost_cap():
    b = TaskBudget()
    b.cost_usd = TASK_BUDGET_USD + 0.01
    with pytest.raises(BrowserBudgetExceeded):
        b.check()


def test_budget_trips_on_wall_clock():
    b = TaskBudget()
    # simulate a start far in the past
    b.started_at = time.monotonic() - 100000
    with pytest.raises(BrowserBudgetExceeded):
        b.check()


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("BOOKIE_USE_BROWSERBASE", raising=False)
    monkeypatch.delenv("BOOKIE_BROWSER_HEADED", raising=False)
    cfg = load_config_from_env()
    assert isinstance(cfg, BrowserConfig)
    assert cfg.use_browserbase is False
    assert cfg.headed is False
    assert str(cfg.storage_state_path).endswith("qbo-storage-state.json")


def test_load_config_browserbase_flag(monkeypatch):
    monkeypatch.setenv("BOOKIE_USE_BROWSERBASE", "1")
    cfg = load_config_from_env()
    assert cfg.use_browserbase is True


def test_is_available_false_without_stagehand():
    # Stagehand is not installed in the test env, so is_available must be False
    # (and must not raise).
    assert is_available() is False


def test_import_stagehand_raises_cleanly():
    with pytest.raises(browser.BrowserError):
        browser._import_stagehand()
