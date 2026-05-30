"""Tests for the QBO report-pack parser. Fixtures match the verified QBO
report response envelope (Header/Columns/Rows with ColData/Summary nesting)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.reports import parse_report, render_markdown, Report


PNL_FIXTURE = {
    "Header": {
        "ReportName": "ProfitAndLoss", "ReportBasis": "Cash",
        "StartPeriod": "2026-01-01", "EndPeriod": "2026-03-31",
        "NoReportData": False,
    },
    "Columns": {"Column": [
        {"ColTitle": "", "ColType": "Account"},
        {"ColTitle": "Total", "ColType": "Money"},
    ]},
    "Rows": {"Row": [
        {
            "Header": {"ColData": [{"value": "Income"}, {"value": ""}]},
            "Rows": {"Row": [
                {"ColData": [{"value": "Consulting", "id": "82"}, {"value": "9000.00"}], "type": "Data"},
                {"ColData": [{"value": "Product Sales", "id": "83"}, {"value": "3000.00"}], "type": "Data"},
            ]},
            "Summary": {"ColData": [{"value": "Total Income"}, {"value": "12000.00"}]},
            "type": "Section", "group": "Income",
        },
        {
            "Header": {"ColData": [{"value": "Expenses"}, {"value": ""}]},
            "Rows": {"Row": [
                {"ColData": [{"value": "Software", "id": "91"}, {"value": "1200.00"}], "type": "Data"},
                {"ColData": [{"value": "Contractors", "id": "92"}, {"value": "4500.00"}], "type": "Data"},
            ]},
            "Summary": {"ColData": [{"value": "Total Expenses"}, {"value": "5700.00"}]},
            "type": "Section", "group": "Expenses",
        },
        {
            "Summary": {"ColData": [{"value": "Net Income"}, {"value": "6300.00"}]},
            "type": "Section", "group": "NetIncome",
        },
    ]},
}


def test_parses_header():
    r = parse_report(PNL_FIXTURE)
    assert r.name == "ProfitAndLoss"
    assert r.basis == "Cash"
    assert r.start_period == "2026-01-01"
    assert r.end_period == "2026-03-31"
    assert r.no_data is False


def test_columns_extracted():
    r = parse_report(PNL_FIXTURE)
    assert r.columns == ["", "Total"]


def test_data_lines_have_account_ids():
    r = parse_report(PNL_FIXTURE)
    consulting = next(l for l in r.lines if l.label == "Consulting")
    assert consulting.account_id == "82"
    assert consulting.values == ["9000.00"]
    assert consulting.is_summary is False


def test_summary_lines_flagged():
    r = parse_report(PNL_FIXTURE)
    total_income = next(l for l in r.lines if l.label == "Total Income")
    assert total_income.is_summary is True
    assert total_income.values == ["12000.00"]


def test_total_for_helper():
    r = parse_report(PNL_FIXTURE)
    assert r.total_for("Net Income") == "6300.00"
    assert r.total_for("Total Income") == "12000.00"
    assert r.total_for("nonexistent") is None


def test_nested_section_depth():
    r = parse_report(PNL_FIXTURE)
    # Income section header at depth 0, its data lines at depth 1
    income_hdr = next(l for l in r.lines if l.label == "Income" and not l.is_summary)
    consulting = next(l for l in r.lines if l.label == "Consulting")
    assert consulting.depth > income_hdr.depth


def test_section_with_only_summary_tolerated():
    # NetIncome section has no Header and no child Rows — must not crash
    r = parse_report(PNL_FIXTURE)
    assert r.total_for("Net Income") == "6300.00"


def test_no_data_report():
    payload = {
        "Header": {"ReportName": "BalanceSheet", "ReportBasis": "Cash",
                   "NoReportData": True},
        "Columns": {"Column": [{"ColTitle": ""}]},
        "Rows": {"Row": []},
    }
    r = parse_report(payload)
    assert r.no_data is True
    assert r.lines == []


def test_missing_keys_dont_crash():
    # Minimal/garbage payloads must parse without raising
    assert parse_report({}).lines == []
    assert parse_report({"Rows": {}}).lines == []
    assert parse_report({"Rows": {"Row": [{}]}}) is not None


def test_render_markdown_contains_totals():
    r = parse_report(PNL_FIXTURE)
    md = render_markdown(r)
    assert "ProfitAndLoss" in md
    assert "Net Income" in md
    assert "6300.00" in md
    assert "Consulting" in md
