# Bookie

Autonomous AI bookkeeper for John Husband's businesses. Built and operated by Claude Code (Chief of Staff to John).

**Status:** Pre-build. Research and design phase, 2026-05-27.

## What Bookie is

A specialist AI employee that handles end-to-end bookkeeping (transaction categorization, bank reconciliation, AR/AP, sales tax tracking, 1099s, month-end close, CPA year-end packet) for John's LLCs. Bookie writes to QuickBooks Online via API, reads bank feeds via Plaid, and reports up through Claude Code (the Chief of Staff) — never directly to John.

## How to read this repo

Read in this order:

1. **`lessons/CTO-postmortem-for-Bookie.md`** — what went wrong with the previous agent project (CTO). The mistakes Bookie must not repeat.
2. **`lessons/Bookie-design-research-synthesis.md`** — the consolidated design input across all five research streams. The "what to build" doc.
3. **`research/`** — the raw research stream outputs (QuickBooks API, competitive landscape, workflow domain, architecture, compliance). Source material behind the synthesis.
4. **`lessons/browser-automation-escalation-ladder.md`** — how Bookie should approach any website it needs to interact with (bank portals, vendor invoices, receipts).
5. **`prd/`** — product requirements doc (written next).
6. **`docs/`** — additional design and operations documentation.

## Reporting structure

```
John (CEO)
   ↑
Claude Code (Chief of Staff)  ← every Bookie ask lands here
   ↑
Bookie (AI bookkeeper)
```

Bookie never contacts John directly. Bookie writes asks, status, and escalations to its log file; Claude Code reads them when online and handles or escalates.

## Sibling projects

- **OpenHarness** (github.com/johnjhusband/OpenHarness) — the harness Claude Code runs on, modeled on patterns from CTO's Hermes and OpenClaw. Bookie runs as a hosted agent inside OpenHarness.
- **CTO-artifacts** (github.com/johnjhusband/CTO-artifacts, private) — captured artifacts from the CTO project. Lessons docs originated here.
- **CTO** (github.com/johnjhusband/CTO, public) — sunsetted previous agent project. Source for postmortem lessons.
