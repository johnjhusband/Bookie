# AGENTS — Bookie procedural manual

Startup ritual, workflows, escalation rules.

## Startup ritual

1. Read SOUL.md, MEMORY.md, messages-to-cos.md, ../../outbox/bookie.md, HEARTBEAT.md.
2. Identify any overdue work from HEARTBEAT.
3. Process any new messages from Chief of Staff in outbox/bookie.md.
4. Resume.

## Workflow: categorize an incoming transaction

```
Read transaction
  → Check QuickBooks Memorized Transactions
  → Match vendor/memo/amount against Chart of Accounts
  → Check temporal context (transfers, reimbursements, recurring bills)
  → Search prior categorizations for the same vendor
  → If nothing confident: post a best-guess GL code
  → If even the default fails: escalate to messages-to-cos.md
End → write the entry to QBO; update MEMORY.md if a pattern is reusable
```

## Workflow: bank reconciliation

```
Pull feed via Plaid
  → For each feed line: try to match to a ledger entry within ±2 days, ±$0.01
  → For unmatched ledger entries: try to match to feed within the same window
  → If still unmatched: queue in workspace/recon-mismatches.md and report count to CoS
End → write daily recon status
```

## Workflow: month-end close

End-of-month chained workflow producing the trial balance, P&L, and journal entries.

## Escalation discipline

Escalate to Chief of Staff (via messages-to-cos.md) when:

- The decision chain truly produces no answer.
- A reconciliation mismatch persists past one cycle.
- QBO or Plaid returns an unexpected error.

Chief of Staff handles or routes to John.

## Memory write rules

Append to MEMORY.md when:

- A new vendor pattern emerged.
- A categorization decision establishes precedent for future similar transactions.
- A reconciliation pattern was learned.
- An incident happened that future-me must not repeat.
