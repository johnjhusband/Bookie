---
name: month-end-close
description: Multi-step monthly close. Pulls final feeds, runs reconciliation, drafts accruals/prepaids/depreciation, produces trial balance + P&L, notifies CoS for sign-off, posts entries to QBO on approval.
user-invocable: false
hidden: false
metadata:
  bookie:
    entry: "bookie.close.run_month_end_close"
    requires:
      modules: ["bookie.close", "bookie.qbo", "bookie.reconciler"]
      openharness:
        checkpoint: true       # uses OpenHarness checkpoint primitive
        policy_guard: true     # every QBO write wrapped
---

# month-end-close

Monthly long-running task. Runs day 1 of each month against the prior month.

## Workflow (with checkpoint at each step)

```
task_id = "close-2026-04"

Step 1: pull final bank feeds for the closing month
  → checkpoint.save(task_id, "feeds-pulled", {...})

Step 2: run reconciliation — escalate on any unmatched items
  → checkpoint.save(task_id, "recon-complete", {...})

Step 3: draft accrual entries (vendor bills received post-period, etc.)
  → checkpoint.save(task_id, "accruals-drafted", {...})

Step 4: draft prepaid amortization (insurance, annual subs, etc.)
  → checkpoint.save(task_id, "prepaids-drafted", {...})

Step 5: draft depreciation entries
  → checkpoint.save(task_id, "depreciation-drafted", {...})

Step 6: produce draft trial balance + P&L → workspace/reports/YYYY-MM-close.md
  → checkpoint.save(task_id, "tb-drafted", {...})

Step 7: notify CoS that close is ready; pause for sign-off
  → checkpoint.save(task_id, "awaiting-signoff", {...})

Step 8: on CoS sign-off, post all drafts to QBO (each wrapped in policy.guard)
  → checkpoint.save(task_id, "posted", {...})

checkpoint.complete(task_id)
```

## Resume behavior

If the daemon crashes mid-close, restart resumes from the last saved step. Hash of workspace state captured in each checkpoint to detect divergence — if the books changed between steps, fail and re-run from Step 1.

## CoS sign-off mechanism

Step 7 writes a structured note to messages-to-cos.md with the draft TB/P&L attached. CoS reads on next tick, either signs off (writes "approved" to outbox/bookie.md) or routes specific concerns. On approval, Step 8 fires.

## Escalation

- Unmatched recon items > $1000 at Step 2 → escalate; close pauses
- Trial balance fails invariants (debits ≠ credits) at Step 6 → escalate hard; do NOT post
- QBO write failure at Step 8 → escalate with the failing entry id; previously-posted entries are NOT auto-reversed

## Output artifact

`workspace/reports/YYYY-MM-close.md`:
- Executive summary (one paragraph)
- Trial balance (table)
- P&L (table)
- Balance sheet (table)
- List of accrual/prepaid/depreciation entries posted
- Unmatched items resolved during close
- Cost of LLM calls for this close (for budget tracking)
