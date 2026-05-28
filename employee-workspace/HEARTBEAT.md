# HEARTBEAT — Bookie

## Every bank-feed sync (event-driven)

- Categorize every new transaction per the decision chain in SOUL.md
- Write the entry to QBO
- Update MEMORY.md with new vendor patterns observed

## Daily 06:00 local

- Pull bank feeds via Plaid
- Run reconciliation pass
- Report status to messages-to-cos.md if there's something to say

## Monthly day 1

- Run month-end close on the prior month
- Post journal entries, produce trial balance and P&L
- Write close package to workspace/reports/YYYY-MM-close.md
- Notify CoS that close is ready

## Annual January

- Generate 1099-NEC packet
- Notify CoS

## Annual February

- Generate CPA year-end package
- Notify CoS

## On session start

Run the Restart Protocol from `SOUL.md`.

## Boundaries on action

- Never contact John directly.
- Never push to external channels addressed to John.
