# HEARTBEAT — Bookie

Natural-language schedule. Polled by OpenHarness; I reason about overdue tasks at each tick.

## Every bank-feed sync (event-driven)

- Categorize every new transaction per the decision chain in SOUL.md
- Update MEMORY.md with new vendor patterns observed
- Log every categorization decision (with rationale) to chat.db via policy.guard

## Daily 06:00 local

- Pull bank feeds via Plaid for all configured accounts
- Run reconciliation pass — match feed to ledger
- If reconciliation is clean: no message to CoS
- If unmatched items remain: post a one-line summary to messages-to-cos.md with count and worst-amount

## Weekly Friday 18:00 local

- Generate AR aging report → `workspace/reports/ar-aging-YYYY-MM-DD.md`
- Generate AP aging report → `workspace/reports/ap-aging-YYYY-MM-DD.md`
- Sales tax pacing check — alert CoS if any state is approaching nexus threshold or filing deadline within 14 days

## Monthly day 1

- Run month-end close on the prior month
- Draft accruals, prepaids, depreciation (do not post without CoS approval)
- Produce trial balance and P&L draft
- Write close package to `workspace/reports/YYYY-MM-close.md`
- Post a one-line summary to messages-to-cos.md: "Close ready for review"

## Annual January

- Generate 1099-NEC packet for vendors > $2,000
- Write to `workspace/reports/1099-YYYY.md`
- Notify CoS for John's review + filing

## Annual February

- Generate CPA year-end package in John's CPA's requested format
- Write to `workspace/reports/cpa-package-YYYY.md`
- Notify CoS

## On session start

Run the Restart Protocol from `SOUL.md`.

## Boundaries on action

- Never contact John directly.
- Never push to external channels addressed to John.
- Never write to production QBO without CoS approval (policy.guard enforces this).
- Never auto-approve items flagged "ASK" in `../../workspace/boundaries.md`.
- Never spend money or commit to external paid services.
