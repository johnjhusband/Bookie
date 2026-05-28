# Bookie — Product Requirements Document

**Version:** 0.1 (pre-build)
**Author:** Chief of Staff (Claude Code), 2026-05-27
**Status:** Draft, ready for build

---

## 1. What Bookie is

Bookie is an **autonomous AI bookkeeper** — an AI employee that handles end-to-end bookkeeping for John Husband's businesses. Bookie is the first AI employee in John's AI organization, running inside the OpenHarness runtime under Chief of Staff supervision.

Bookie's job: keep John's books current, accurate, audit-ready, and require near-zero interruption of John's time. The bar is **categorize by default; ask only when truly stuck.**

## 2. Reporting structure

```
John (CEO)
   ↑
Chief of Staff (Claude Code in OpenHarness)
   ↑
Bookie
```

Bookie never contacts John directly. Bookie writes to `inbox/bookie.md` in OpenHarness; Chief of Staff handles or escalates. Bookie reads from `outbox/bookie.md` for direction.

## 3. Scope (v1)

**In scope, in priority order:**

1. **Transaction categorization** — every transaction, auto-coded by default.
2. **Bank reconciliation** — feed-to-ledger matching.
3. **AR/AP cadence** — invoice sends, payment matches, vendor bill capture.
4. **Sales tax tracking** — nexus monitoring, return drafting (not filing).
5. **1099-NEC tracking** — vendor totals through the year, January packet.
6. **Month-end close** — chained workflow producing trial balance and journal entries.
7. **CPA year-end package** — clean handoff in the format John's CPA wants.

**Out of scope (v1):**

- Tax-planning advice
- Investment advice
- Payroll tax filing
- Anything Bookie would have to sign for
- Multi-tenant / serving other people's books (compliance jumps; see §11)

## 4. The decision rule that defines Bookie

**Categorize by default. Never ask unless truly stuck.**

For every incoming transaction, Bookie runs this chain in order:

1. **QuickBooks Memorized Transactions** — if QBO has a memorized rule that matches vendor/amount/pattern, use it. **No ask.**
2. **Transaction context** — vendor name, memo line, amount, account, date. Pattern-match against the locked Chart of Accounts.
3. **Temporal context** — what other transactions and activities happened around the same time. Look for related expense+reimbursement pairs, recurring monthly bills on expected days, transfer-pairs within minutes.
4. **Historical similarity** — search prior categorizations for the same vendor or similar amount/pattern; replicate the prior decision.
5. **Default categorization with confidence tag** — even with low confidence, **post the entry** with a best-guess GL code and tag it `bookie-confidence=low`. John can review tagged items in a weekly batch if he chooses; he is **never asked transaction-by-transaction**.
6. **Ask Chief of Staff (not John)** — only when none of the above produces a defensible answer. Chief of Staff handles ~95% of these without escalating further. John sees only items Chief of Staff also can't resolve.

**Bookie does not maintain a "transactions awaiting John's approval" queue.** Bookie maintains a "transactions I wasn't sure about" log, sorted by dollar amount and unusualness, that John reads on his schedule if he wants.

## 5. Agent topology

Following the 2026 consensus for production financial AI agents (Digits, Puzzle, Truewind): **supervisor + narrow specialists, typed-state graph, no ReAct.**

- **Supervisor** — decomposes work ("close April books") into discrete steps and dispatches to specialists.
- **`categorizer`** — runs the decision chain above for each transaction.
- **`reconciler`** — matches bank-feed transactions to ledger entries.
- **`journal-writer`** — drafts accruals, prepaids, depreciation entries for month-end.
- **`reporter`** — produces trial balance, P&L, balance sheet, sales-tax drafts, year-end CPA packet.
- **`tax-prep-helper`** (optional, v2) — generates 1099 packet and sales tax drafts (drafts only, never files).

Pattern: **plan → structured tool call → deterministic verify → commit.** No ReAct loops; no Reflexion. Bounded execution per task.

## 6. Decide-vs-propose split

LLM proposes; deterministic rule engine decides. The LLM never writes to the ledger directly.

- **95% confidence threshold** to auto-commit categorization (industry de facto bar).
- **Invariants enforced outside the LLM:** debits == credits, trial balance reconciles, sum(splits) == total. Deterministic code that the LLM cannot route around.
- **Threshold gates:**
  - New vendor → categorize with `bookie-confidence=low` tag, do not auto-create a memorized transaction.
  - New GL account → never auto-create; route to Chief of Staff (then John if needed).
  - Journal entry → in v1, always escalate to Chief of Staff before posting.
  - Transaction > $10,000 → escalate to Chief of Staff (initial ceiling, tunable per `boundaries.md`).

## 7. Integrations

- **QuickBooks Online** via REST v3 + OAuth 2.0 (Intuit's only supported auth).
  - 5-year refresh token cap. Bookie auto-renews before expiry.
  - Idempotency: `Request-Id` header per mutation, persisted to disk before the API call fires.
  - Optimistic concurrency: `SyncToken` on every entity write.
  - Webhooks: CloudEvents format (mandatory after 2026-05-15).
  - SDK: `python-quickbooks` + `intuit-oauth`.
  - Dev: QBO free sandbox tenant provisioned in install script.
- **Plaid** for bank feeds (OAuth-only banks; ~90% of US major banks).
  - No password storage. Ever.
  - SOC 2 + ISO 27001 vendor.
- **OpenHarness state** (`state/chat.db`) — every Bookie action logged.

No direct bank scraping. No Yodlee. No screen scraping.

## 8. Sandbox / dry-run / shadow mode

Three execution modes — all required before any production write:

- **Sandbox** — Bookie wired to QBO sandbox tenant by default. Every developer uses sandbox first.
- **Dry-run** — `--dry-run` flag emits the planned QBO mutation as JSON to disk without executing. Default for new specialists for the first week.
- **Shadow mode for production cutover** — Bookie runs in parallel with John's existing process for a calendar month, writes nothing to production QBO, produces a daily diff report comparing what Bookie would have done vs. what John actually did. Only after diffs are < 2% material does Bookie get write access to production.

This is the single biggest insurance policy against the "agent says it tested" failure mode CTO died on.

## 9. Workspace (under OpenHarness)

Bookie lives at `~/.openharness/employees/bookie/`:

```
employees/bookie/
  SOUL.md           # Bookie's identity (auto-categorize by default, etc.)
  USER.md           # About John (CEO), via Chief of Staff
  MEMORY.md         # Bookie's accumulated knowledge — vendor rules, CoA, prior categorizations
  AGENTS.md         # Bookie's procedural manual — close cadence, escalation rules
  HEARTBEAT.md      # Bookie's schedule — daily feed pull, weekly recs, monthly close
  STYLE.md          # Bookie's voice (when talking to CoS)
  TOOLS.md          # QBO API, Plaid, file ops
  boundaries.md     # Bookie's own boundary table (defers to OpenHarness boundaries.md)
  messages-to-cos.md  # alias for ~/.openharness/inbox/bookie.md
  workspace/
    decisions/      # categorization decisions, audit trail
    drafts/         # in-progress JEs, drafts not yet posted
    reports/        # monthly close packages, year-end packets
```

The full Bookie repo (this one) holds source code, install scripts, and design docs. The OpenHarness employee folder holds Bookie's running state.

## 10. State / audit trail

Append-only, hash-chained, tamper-evident. Schema captures `(observation, decision_rationale, tool_call, result, model_version, prompt_version, timestamp, idempotency_key)` for every Bookie action.

- **Retention:** 7 years (covers IRS Topic 305 baseline, 7-year cases for bad debt / understatement, and CA FTB 4-year minimum).
- **Storage:** `employees/bookie/workspace/audit/YYYY-MM/` Markdown rollovers + `state/chat.db` indexed view.
- **Reference:** QBO's own Audit Log is the UX target. Bookie's output should be openable in QBO Audit Log and recognizable.

## 11. Compliance line (binding)

**V1 is self-use only.** John's businesses, John's QBO tenants, John's bank accounts.

The moment Bookie touches anyone else's books, John becomes a GLBA "financial institution" under FTC Safeguards Rule (16 CFR 314). At that point Bookie must:

- Be SOC 2 Type II (or be wrapped in a SOC 2 entity)
- Add ISO 27001 + ISO 42001 (AI management system) per 2026 buyer expectations
- Pass a written risk assessment / pen-test / IR plan (waived under 5,000 consumers but still recommended)
- Carry E&O / cyber liability ($1-2M)

**Non-negotiables even for self-use:**

1. OAuth-only bank connections via Plaid.
2. AES-256 at rest, TLS 1.2+ in transit.
3. MFA on every system that touches financial data.
4. Tamper-evident 7-year audit log.
5. Human-approval gate on every write to QBO, every tax filing, every payment. Always.
6. **No investment advice. No income-tax-planning advice.** Bookie describes what the data shows. Bookie does not prescribe what John should do. This is the legal line between bookkeeping (no license) and tax/investment advice (CPA/EA/RIA).

## 12. Cost control

Pattern from the architecture research:

- **Three-tier model routing:** cheap model for categorization classification, mid-tier for journal entries, top-tier only for ambiguous calls and month-end synthesis.
- **Prompt caching** on the locked CoA + vendor list (Anthropic prompt caching, ~50-90% discount on cached prefixes).
- **Batched processing** — Bookie doesn't run a continuous loop; triggers on bank-feed updates plus a once-daily sweep.
- **Hard caps per task:** per-task LLM call cap (20), per-day token budget ($1/day initial), retries capped at 2 then escalate.

## 13. Heartbeat schedule

```markdown
# HEARTBEAT — Bookie

## Every bank-feed sync (event-driven)
- Categorize every new transaction per the decision chain
- Update MEMORY.md with new vendor patterns

## Daily 06:00 local
- Pull bank feeds via Plaid for all configured accounts
- Run reconciliation pass
- Write status to messages-to-cos.md (only if there's something to say)

## Weekly Friday 18:00 local
- Generate AR aging
- Generate AP aging
- Sales tax pacing check — alert CoS if any state is approaching nexus or filing deadline

## Monthly day 1
- Run month-end close on prior month
- Draft accruals, prepaids, depreciation
- Produce trial balance and P&L draft
- Write close package to workspace/reports/YYYY-MM-close.md
- Notify CoS that close is ready for sign-off

## Annual January
- Generate 1099-NEC packet (vendors > $2,000 threshold)
- Notify CoS for John's review + filing

## Annual February
- Generate CPA year-end package per John's CPA's requested format
```

## 14. Phasing

**Phase 1 (this build):**
- Bookie workspace scaffold under OpenHarness employees/
- Python skeleton: `categorizer.py`, `reconciler.py` (stubs)
- QBO sandbox config placeholder
- Plaid integration design docs (no live wiring)
- The categorization decision chain implemented as a pure-function unit (no QBO writes)

**Phase 2:**
- QBO sandbox wired live
- Plaid wired live for one bank
- Dry-run mode functional end-to-end
- One month of shadow-mode running

**Phase 3:**
- Production cutover after shadow-mode diff < 2% material
- Full close workflow live
- Sales tax draft generation
- Audit log fully populated

**Phase 4:**
- 1099 packet generation
- CPA year-end package
- Tax-prep-helper specialist (drafts only)

## 15. Success criteria

- **S1.** Bookie categorizes every incoming transaction without asking John. Bookie's "transactions I wasn't sure about" log has fewer than N items per week (N tunable; initial target: ≤ 5).
- **S2.** Reconciliation runs clean — bank feed matches ledger to within $0.01.
- **S3.** Month-end close package produced in ≤ 4 calendar days.
- **S4.** Audit log captures every Bookie action with reasoning. Pass an audit sample test.
- **S5.** No transaction is written to production QBO without explicit Chief of Staff approval (which may be auto-approved per boundaries.md, but is logged either way).
- **S6.** Zero notifications pushed to John's phone or any external channel. Zero.

## 16. References

- Bookie design synthesis: `lessons/Bookie-design-research-synthesis.md`
- CTO postmortem: `lessons/CTO-postmortem-for-Bookie.md`
- Browser ladder: `lessons/browser-automation-escalation-ladder.md`
- Raw research: `research/01-quickbooks-api.md` through `research/05-compliance-security.md`
- OpenHarness PRD: `https://github.com/johnjhusband/OpenHarness/blob/master/prd/OpenHarness-PRD.md`

## 17. Open questions

- **One business or three?** John's LLCs include Husband.LLC; need a full list and decide if Bookie is multi-tenant from day one or single-tenant first then forked.
- **CPA's requested handoff format?** QBO Accountant access vs. flat-file packet. Ask John.
- **Cash vs. accrual basis?** Probably both (cash for tax, accrual for management). Confirm.
- **First-month shadow mode start date?** Determines critical-path timeline. Pending Phase 2 readiness.

These are pre-build design clarifications, not blockers. Chief of Staff queues them for John when Bookie reaches the relevant phase.
