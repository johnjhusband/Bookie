# Bookie — Product Requirements Document

**Version:** 0.3 (post re-research)
**Author:** Chief of Staff (Claude Code), 2026-05-28
**Status:** Replaces v0.2 entirely.

This PRD is the implementation lens. The source-of-truth for what Bookie does is `prd/requirements.md` — every line there traces to John's words or a cited integration contract. This PRD describes how those requirements map to code.

---

## 1. What Bookie is

Bookie is an autonomous AI bookkeeper for John and Tara Husband, dba Husband.LLC (Florida, Form 1065 partnership, cash basis). Bookie runs inside OpenHarness under Chief of Staff supervision and operates the QuickBooks Online tenant via two surfaces:

- **REST API** for what QBO exposes programmatically (CoA, vendors, posted transactions, JournalEntry posts, reports, Attachable, RecurringTransaction reads).
- **Browser automation** for the 7 documented API gaps (For Review queue, Bank Rules CRUD, Reconcile workflow, Receipt inbox match, Audit Log, force-match, RecurringTransaction writes).

John's words (2026-05-28): *"the AI should also be able to interact with the software graphically like a human... I want the full experience. If the API can't do something I want to have the graphic interface already built and working."*

## 2. Reporting structure

```
John (CEO)
   ↑
Chief of Staff (Claude Code in OpenHarness)
   ↑
Bookie
```

Bookie never contacts John. Writes to `inbox/bookie.md`; Chief of Staff handles or routes.

## 3. Scope (traceable)

See `prd/requirements.md` for the full requirement set with sources. In summary:

- **R1.** Categorize every QBO transaction
- **R2.** Six-step decision chain (memorized → context → temporal → historical → default → escalate)
- **R3.** Inspection-on-connect: pull CoA + vendors + posted-txn history + recurring on first credential availability
- **R4.** CPA report pack (cash basis, with comparatives)
- **R5.** Monthly pre-handoff cleanup (zero out Uncategorized buckets, reclassify owner draws, reconcile, etc.)
- **R6.** Form 1065 CoA structure (per-partner equity accounts for John and Tara)
- **R7.** Browser automation for the 7 documented API gaps
- **R8.** Two-surface decision logic (API where it works, browser where it must)
- **R9.** Cash-basis-specific posture (Purchase over Bill, no depreciation booking)
- **R10.** Domain-specific categorization patterns (home office, vehicle, draws, mixed personal/business, estimateds)
- **R11.** Annual 1099-NEC packet (opportunistic; $2,000 threshold; only if vendors cross)
- **R12.** Daily/weekly/monthly/quarterly/annual reporting cadence to CoS
- **R13.** Banned features (Plaid, sandbox, sales tax tracking, AR/AP cadence as a subsystem, depreciation booking, etc.)
- **R14.** John's real-world prereqs (Intuit dev account, Bookie bot Intuit user, one-time MFA)
- **R15.** Success criteria

## 4. Architecture

### 4.1 Two surfaces

The split is documented per requirement R8. The daemon picks API or browser per task; the split is not configurable per call.

**API surface** (`bookie.qbo`):
- `load_config`, `save_config`, `refresh_access_token`
- `fetch_chart_of_accounts`, `fetch_vendors`, `fetch_memorized_transactions`
- `post_journal_entry`, `update_entity`
- (Future) `fetch_posted_transactions`, `fetch_reports`, `upload_attachable`

**Browser surface** (`bookie.browser`):
- `list_for_review`, `categorize_for_review_item`, `force_match`
- `list_bank_rules`, `create_bank_rule`
- `reconcile_account`
- `attach_and_match_receipt`
- `read_audit_log`
- `is_available()` — returns True only if Stagehand is importable AND a persisted storage state exists

Browser uses Stagehand for AI-prompted actions (selectors are unstable per QBO research). Local Chromium by default; Browserbase opt-in via `BOOKIE_USE_BROWSERBASE=1`.

### 4.2 The categorizer

`bookie.categorizer.categorize()` — pure function, no I/O, always returns a `Categorization` per requirements.md R2. Six-step chain; step 5 always succeeds; step 6 escalation is the unreachable-in-practice safety hatch.

### 4.3 The tick

`bookie.tick(context)` is the OpenHarness daemon entrypoint. Flow:

```
if no QBO credentials yet → status: idle-no-qbo-creds
if not yet inspected → run R3 first-inspection; report findings; status: first-inspection-complete
else:
    process_uncategorized_via_api()      # R5 reclassification of Uncategorized buckets
    if BOOKIE_BROWSER_TICK=1 and browser.is_available():
        list_for_review() and report queue size
return tick result for OpenHarness daemon
```

### 4.4 OpenHarness integration

Bookie remains a workspace folder under `OpenHarness/employees/bookie/`. The daemon imports `bookie` and calls `bookie.tick(context)`. Every QBO write Bookie makes is wrapped in `openharness.policy.guard()`.

### 4.5 Hard stops (browser side)

Per `lessons/browser-automation-escalation-ladder.md`:
- 5 min wall clock per browser task
- 50 LLM calls per task
- $2 cost ceiling per task
- 10 attempts per site per day

Enforced in `bookie.browser.TaskBudget`.

## 5. State + audit trail

Per-tick artifacts persist under `OpenHarness/employees/bookie/workspace/`:

- `inspection/` — R3 raw QBO snapshots (coa.json, vendors.json, recurring.json)
- `decisions/YYYYMMDD-HHMMSS-*.json` — every categorization decision with rationale
- `posted/<tx_id>.json` — every QBO write that landed
- `reports/YYYY-MM-*.md` — monthly + annual CPA package outputs
- `state/first-inspection.json` — marker file so R3 only fires once

OpenHarness chat.db logs every Bookie action with the `kind` taxonomy already in place (`tick`, `event`, `escalation`, `inbox`, etc.). 7-year retention per OpenHarness PRD §12.

## 6. Phasing

- **Phase 1 (done):** QBO API client (live, real REST v3 + OAuth refresh). Categorization decision chain (9 tests passing). Bookie workspace files real. Bookie.tick() restructured for QBO-only flow.
- **Phase 2 (this build):** Inspection-on-connect (R3). Uncategorized-bucket reclassification (R5 minimal). Browser scaffolding (`bookie.browser`).
- **Phase 3:** Live QBO write of the reclassification (currently logs the recommendation; needs the API update call). First end-to-end browser pass against your sandbox QBO. Monthly cleanup checklist via browser + API.
- **Phase 4:** Full report-pack production. 1099 packet generation. Browser-driven Reconciliation workflow.

## 7. References

- Requirements: `prd/requirements.md` (canonical, traceable)
- Research streams used to build the requirements:
  - QBO API surface — verified by research agent against Intuit docs, May 2026
  - QBO banking pipeline — verified by research agent
  - CPA hand-off package — verified against AICPA + IRS sources
  - Browser automation viability — verified including Akamai defense, TOS posture, Stagehand viability
- CTO postmortem: `lessons/CTO-postmortem-for-Bookie.md`
- Browser escalation ladder: `lessons/browser-automation-escalation-ladder.md`
- OpenHarness PRD: `https://github.com/johnjhusband/OpenHarness/blob/master/prd/OpenHarness-PRD.md`
