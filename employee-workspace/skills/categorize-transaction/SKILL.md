---
name: categorize-transaction
description: Run the SOUL.md decision chain on a single Transaction; return a Categorization with GL account, confidence, rule_chain_step, rationale.
user-invocable: false
hidden: false
metadata:
  bookie:
    entry: "bookie.categorizer.categorize"
    requires:
      python: ">=3.10"
      modules: ["bookie.models", "bookie.categorizer"]
---

# categorize-transaction

Pure-function categorization. The single most-called skill in Bookie.

## When to use

For every Transaction read from a bank feed, vendor receipt, or manual entry.

## Decision chain (per Bookie SOUL.md)

1. QuickBooks Memorized Transactions match → use it (confidence 1.00)
2. CoA pattern match on vendor / memo → use it (confidence 0.90)
3. Temporal context (transfer-pair, expense+reimbursement, recurring bill) → use it (confidence 0.80)
4. Historical similarity (same vendor categorized before) → replicate (confidence 0.75)
5. Default best-guess (Uncategorized Income / Expense) tagged `bookie-confidence=low` (confidence 0.40)
6. Escalate to CoS — only if the chain itself crashes; never reached in normal flow

## Inputs

```python
categorize(
    tx: Transaction,
    *,
    memorized_rules: Iterable[MemorizedRule] = (),
    coa_patterns: dict[str, list[str]] | None = None,
    neighbors: Iterable[Transaction] = (),
    history: Iterable[Categorization] = (),
    prior_lookup: dict[str, Transaction] | None = None,
) -> Categorization
```

## Output

Always returns a `Categorization`. Never returns None. Never raises.

## Invariants (test-enforced)

- Output `gl_account` is non-empty.
- `requires_escalation` is False (the chain always produces an answer).
- Inflows default to "Uncategorized Income"; outflows to "Uncategorized Expense".

## Calling site

`bookie.tick()` calls this for every Transaction it pulls from QBO's Uncategorized buckets via the API (Purchases assigned to "Uncategorized Expense", "Uncategorized Income", "Ask My Accountant"). Result is logged to `workspace/decisions/YYYYMMDD-HHMMSS-*.json` and (when the live QBO update is wired) any reclassification is wrapped in OpenHarness `policy.guard()`.

When the browser surface is active (BOOKIE_BROWSER_TICK=1 + Stagehand storage state present), Bookie also drives the QBO "For Review" queue and uses this same categorizer to pick the GL code for each line.
