# Bookie — Product Requirements Document

**Version:** 0.2 (scope-corrected)
**Author:** Chief of Staff (Claude Code), 2026-05-27
**Status:** Draft

---

## 1. What Bookie is

Bookie is an autonomous AI bookkeeper for John Husband's businesses. The first AI employee in John's AI organization, running inside the OpenHarness runtime under Chief of Staff supervision.

Bookie's job: keep John's books current and accurate while requiring near-zero interruption of John's time.

## 2. Reporting structure

```
John (CEO)
   ↑
Chief of Staff (Claude Code in OpenHarness)
   ↑
Bookie
```

Bookie never contacts John directly. Bookie writes to `inbox/bookie.md`; Chief of Staff handles or routes.

## 3. Scope

- Transaction categorization
- Bank reconciliation
- AR / AP cadence
- Sales tax tracking
- 1099-NEC tracking
- Month-end close
- CPA year-end package

## 4. The decision rule

**Auto-categorize every transaction. Don't ask John.**

For every incoming transaction, run this chain in order:

1. **QuickBooks Memorized Transactions** — if QBO has a memorized rule matching vendor/amount/pattern, use it.
2. **Transaction context** — vendor name, memo, amount against the Chart of Accounts.
3. **Temporal context** — surrounding transactions for relationships (transfer-pairs, expense+reimbursement, recurring bills on schedule).
4. **Historical similarity** — search prior categorizations for the same vendor or similar pattern.
5. **Default categorization** — even when nothing matches confidently, post a best-guess GL code (e.g., "Uncategorized Expense") with a `bookie-confidence=low` tag.
6. **Ask Chief of Staff** — only when the chain truly cannot produce an answer.

**Bookie does not maintain a "transactions awaiting John's approval" queue.** Categorization happens by default. The low-confidence items land in a log John can browse if he chooses.

## 5. Agent topology

Supervisor + narrow specialists:

- **Supervisor** — decomposes work and dispatches.
- **`categorizer`** — runs the decision chain on each transaction.
- **`reconciler`** — matches bank-feed transactions to ledger entries.
- **`journal-writer`** — drafts and posts month-end accruals, prepaids, depreciation.
- **`reporter`** — produces trial balance, P&L, balance sheet, sales-tax drafts, year-end CPA packet.

Pattern: plan → tool → verify → commit. Bounded execution, no ReAct loops.

## 6. Integrations

- **QuickBooks Online** via REST v3 + OAuth 2.0.
  - Idempotency via `Request-Id` header.
  - Optimistic concurrency via `SyncToken`.
  - SDK: `python-quickbooks` + `intuit-oauth`.
- **Plaid** for bank feeds (OAuth-only banks).
- **OpenHarness state** (`state/chat.db`) — every Bookie action logged.

## 7. Workspace (under OpenHarness)

Bookie's running workspace lives at `~/.openharness/employees/bookie/`:

```
employees/bookie/
  SOUL.md
  USER.md
  MEMORY.md            # vendor rules, CoA, prior categorizations
  AGENTS.md
  HEARTBEAT.md
  STYLE.md
  TOOLS.md
  messages-to-cos.md   # alias for ~/.openharness/inbox/bookie.md
  workspace/
    decisions/         # categorization decisions
    drafts/            # in-progress reports
    reports/           # close packages, year-end packets
```

The Bookie repo holds source code, install scripts, and design docs. The OpenHarness employee folder holds Bookie's running state. `install.sh` syncs the canonical workspace files from `employee-workspace/` in the repo into the OpenHarness folder.

## 8. Heartbeat schedule

```
Every bank-feed sync (event-driven)
  Categorize every new transaction per the decision chain
  Write the entry to QBO
  Update MEMORY.md with new vendor patterns

Daily 06:00 local
  Pull bank feeds via Plaid
  Run reconciliation pass
  Report to messages-to-cos.md only if there's something to say

Monthly day 1
  Run month-end close on the prior month
  Post journal entries, produce trial balance and P&L
  Notify CoS that close is ready

Annual January
  Generate 1099-NEC packet
  Notify CoS

Annual February
  Generate CPA year-end package
  Notify CoS
```

## 9. Phasing

**Phase 1 (this build):**
- Bookie workspace scaffold under OpenHarness employees/
- Python: `categorizer.py` (decision chain), `models.py`, `qbo.py` (stub), `plaid_feed.py` (file-based for testing), `cli.py`
- Unit tests for the categorizer

**Phase 2:**
- QBO wired live with OAuth
- Plaid wired live for John's bank accounts
- First production transactions flowing

**Phase 3:**
- Month-end close workflow live
- Sales tax draft generation
- 1099 packet generation
- CPA year-end package

## 10. Success criteria

- **S1.** Every incoming transaction is categorized. John is never asked.
- **S2.** Reconciliation runs clean — bank feed matches ledger.
- **S3.** Month-end close produces a complete package.
- **S4.** Bookie reports to Chief of Staff, never to John. Zero notifications to John's phone.

## 11. References

- Bookie design synthesis: `lessons/Bookie-design-research-synthesis.md`
- CTO postmortem: `lessons/CTO-postmortem-for-Bookie.md`
- Raw research: `research/01-quickbooks-api.md` through `research/05-compliance-security.md`
- OpenHarness PRD: `https://github.com/johnjhusband/OpenHarness/blob/master/prd/OpenHarness-PRD.md`
