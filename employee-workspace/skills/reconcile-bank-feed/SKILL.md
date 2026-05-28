---
name: reconcile-bank-feed
description: Match Plaid bank-feed lines to QBO ledger entries within ±2 days, ±$0.01. Queue mismatches; escalate to CoS if persistent.
user-invocable: false
hidden: false
metadata:
  bookie:
    entry: "bookie.reconciler.match_feed_to_ledger"
    requires:
      modules: ["bookie.reconciler", "bookie.qbo", "bookie.plaid_feed"]
---

# reconcile-bank-feed

Daily-cadence skill. Pulls the bank feed, matches each line to a ledger entry, queues anything that doesn't match.

## When to use

- Daily at 06:00 local per HEARTBEAT.md
- Anytime a feed-sync event arrives
- Anytime CoS asks "is the recon clean?"

## Matching rules (in order)

1. **Exact id match** — if the feed line carries a `qbo_id` from a prior write, match directly.
2. **Date + amount + memo** — same date, amount within $0.01, memo substring match.
3. **Date + amount** — within ±2 days, amount within $0.01.
4. **Date + amount soft window** — within ±5 days, amount within $0.01 (for slow-posting transactions).

A feed line that hits no rule and a ledger entry that hits no rule are both "unmatched."

## Output

```python
{
  "account": "checking-8211",
  "as_of": "2026-05-27",
  "feed_lines": 142,
  "ledger_lines": 142,
  "matched": 138,
  "unmatched_feed": [...],         # feed lines with no ledger match
  "unmatched_ledger": [...],       # ledger entries with no feed match
  "status": "clean" | "dirty" | "escalate",
}
```

## Escalation

- `clean`: no message to CoS (silence is the goal)
- `dirty` (1-5 mismatches, all < $1000): post a one-line summary
- `escalate` (>5 mismatches OR any single > $1000): write to escalations.md via OpenHarness

## Side effects

- Persistent unmatched items go to `workspace/recon-mismatches.md`
- chat.db gets a `tick` row with the result
- MEMORY.md gets a `[semantic]` entry if a new matching pattern was learned
