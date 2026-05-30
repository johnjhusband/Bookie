"""QBO report-pack generation: P&L, Balance Sheet, General Ledger, Trial Balance.

All four QBO report endpoints share one response envelope:
    { "Header": {...}, "Columns": {"Column": [...]}, "Rows": {"Row": [...]} }
A Row is either a Data row ({"ColData": [...], "type": "Data"}) or a Section
({"Header": {...}, "Rows": {"Row": [...]}, "Summary": {...}, "type": "Section",
"group": "Income"}). Sections nest recursively (sub-accounts), ending in a
Summary row that holds the section total.

So we write ONE recursive parser and reuse it for every report.

Verified against current Intuit report API docs (May 2026). The parser is
defensive: rows may omit type/Header/Rows/Summary; ColData[i] maps positionally
to Columns.Column[i]; Header.NoReportData=true means zero data; `id` may be
absent on any cell.

This module needs no live QBO connection to be exercised — it parses report
JSON, which the tests supply as fixtures. The fetch_* functions hit the live
API when credentials exist; the parse_* functions are pure.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReportLine:
    """One account line (or summary line) in a report."""
    label: str
    values: list[str]          # one per money column, positional
    account_id: str | None = None
    is_summary: bool = False
    group: str | None = None
    depth: int = 0


@dataclass
class Report:
    name: str
    basis: str                 # "Cash" | "Accrual"
    start_period: str
    end_period: str
    columns: list[str]         # column titles, left to right
    lines: list[ReportLine]
    no_data: bool = False

    def total_for(self, label_substring: str) -> str | None:
        """Return the last money value of the first summary line whose label
        contains label_substring (case-insensitive). e.g. total_for('Net Income')."""
        sub = label_substring.lower()
        for ln in self.lines:
            if ln.is_summary and sub in ln.label.lower() and ln.values:
                return ln.values[-1]
        return None


def _coldata_values(coldata: list[dict]) -> tuple[str, list[str], str | None]:
    """Given a ColData array, return (label, money_values, first_id).
    Column 0 is the label/account; columns 1+ are money values."""
    if not coldata:
        return "", [], None
    label = coldata[0].get("value", "")
    first_id = coldata[0].get("id")
    values = [c.get("value", "") for c in coldata[1:]]
    return label, values, first_id


def _walk(rows: list[dict], out: list[ReportLine], depth: int, group: str | None) -> None:
    for row in rows:
        rtype = row.get("type", "Data")
        if rtype == "Section":
            g = row.get("group", group)
            header = row.get("Header")
            if header and header.get("ColData"):
                label, values, _id = _coldata_values(header["ColData"])
                if label:
                    out.append(ReportLine(label=label, values=values, group=g,
                                          depth=depth))
            inner = (row.get("Rows") or {}).get("Row") or []
            _walk(inner, out, depth + 1, g)
            summary = row.get("Summary")
            if summary and summary.get("ColData"):
                label, values, _id = _coldata_values(summary["ColData"])
                out.append(ReportLine(label=label or f"Total {g or ''}".strip(),
                                      values=values, is_summary=True, group=g,
                                      depth=depth))
        else:
            coldata = row.get("ColData") or []
            label, values, acct_id = _coldata_values(coldata)
            out.append(ReportLine(label=label, values=values, account_id=acct_id,
                                  group=group, depth=depth))


def parse_report(payload: dict) -> Report:
    """Parse any QBO report response into a Report. Pure function."""
    header = payload.get("Header", {}) or {}
    columns_raw = (payload.get("Columns", {}) or {}).get("Column", []) or []
    columns = [c.get("ColTitle", "") for c in columns_raw]
    no_data = bool(header.get("NoReportData", False))
    lines: list[ReportLine] = []
    rows = (payload.get("Rows", {}) or {}).get("Row", []) or []
    _walk(rows, lines, 0, None)
    return Report(
        name=header.get("ReportName", ""),
        basis=header.get("ReportBasis", ""),
        start_period=header.get("StartPeriod", ""),
        end_period=header.get("EndPeriod", ""),
        columns=columns,
        lines=lines,
        no_data=no_data,
    )


def render_markdown(report: Report) -> str:
    """Render a Report as a readable markdown table for the CPA pack."""
    lines = [f"## {report.name or 'Report'} ({report.basis or '?'} basis)"]
    if report.start_period or report.end_period:
        lines.append(f"_{report.start_period} → {report.end_period}_\n")
    if report.no_data:
        lines.append("_(no data for this period)_")
        return "\n".join(lines)
    for ln in report.lines:
        indent = "  " * ln.depth
        money = "  ".join(v for v in ln.values if v) if ln.values else ""
        bullet = "**" if ln.is_summary else ""
        lines.append(f"{indent}- {bullet}{ln.label}{bullet}"
                     + (f": {money}" if money else ""))
    return "\n".join(lines)


# ---------------- live fetchers (need QBO creds) ----------------

def _fetch_report(cfg, creds_path, report_name: str, params: dict) -> dict:
    from bookie.qbo import _api_call
    return _api_call(cfg, creds_path, "GET", f"/reports/{report_name}", params=params)


def fetch_profit_and_loss(cfg, creds_path, *, start: str, end: str,
                          summarize_by: str = "Total") -> Report:
    payload = _fetch_report(cfg, creds_path, "ProfitAndLoss", {
        "start_date": start, "end_date": end,
        "accounting_method": "Cash", "summarize_column_by": summarize_by,
    })
    return parse_report(payload)


def fetch_balance_sheet(cfg, creds_path, *, start: str, end: str) -> Report:
    payload = _fetch_report(cfg, creds_path, "BalanceSheet", {
        "start_date": start, "end_date": end, "accounting_method": "Cash",
    })
    return parse_report(payload)


def fetch_general_ledger(cfg, creds_path, *, start: str, end: str,
                         columns: str = "tx_date,txn_type,doc_num,name,memo,account_name,subt_nat_amount") -> Report:
    # Keep column count modest — >25 columns risks a 504 / 400k-cell cap.
    payload = _fetch_report(cfg, creds_path, "GeneralLedger", {
        "start_date": start, "end_date": end, "accounting_method": "Cash",
        "columns": columns,
    })
    return parse_report(payload)


def fetch_trial_balance(cfg, creds_path, *, start: str, end: str) -> Report:
    payload = _fetch_report(cfg, creds_path, "TrialBalance", {
        "start_date": start, "end_date": end, "accounting_method": "Cash",
    })
    return parse_report(payload)


def build_cpa_pack(cfg, creds_path, *, start: str, end: str) -> str:
    """Fetch all four reports and render a single CPA-handoff markdown package."""
    parts = [f"# CPA Package — {start} to {end} (cash basis)\n"]
    for fetch in (
        lambda: fetch_profit_and_loss(cfg, creds_path, start=start, end=end),
        lambda: fetch_balance_sheet(cfg, creds_path, start=start, end=end),
        lambda: fetch_general_ledger(cfg, creds_path, start=start, end=end),
        lambda: fetch_trial_balance(cfg, creds_path, start=start, end=end),
    ):
        try:
            parts.append(render_markdown(fetch()))
        except Exception as e:
            parts.append(f"## (report failed: {e})")
    return "\n\n".join(parts)
