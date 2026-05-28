---
name: detect-anomaly
description: Run sniff-tests on incoming transactions for fraud / data-quality red flags. Pattern-match, not LLM-judgment. Escalate hits to CoS.
user-invocable: false
hidden: false
metadata:
  bookie:
    entry: "bookie.anomaly.scan"
    requires:
      modules: ["bookie.anomaly"]
---

# detect-anomaly

Pattern-match sniff tests run alongside categorization. Not LLM judgment — deterministic rules. The categorizer handles "what GL code"; this handles "should anyone look at this."

## When to use

For every Transaction processed through `bookie.tick()`. Runs in parallel with categorize-transaction. A transaction can be both categorized AND flagged for review.

## Rules (v1)

1. **Round-number outflow > $1000** — `$2000.00`, `$5000.00`, etc. Often a sign of a typed amount vs. an itemized invoice. Flag.
2. **After-hours card activity** — card transactions between 02:00 and 05:00 local time. Flag.
3. **Duplicate amount within 7 days, same vendor** — could be a double-charge. Flag.
4. **Vendor name never seen before AND amount > $500** — flag.
5. **New geographic location for a card** — flag (when location is in feed metadata).
6. **Velocity spike** — > 5x last month's average daily spend on one card. Flag.
7. **Refund without an originating charge** — flag.

Hits are independent; one transaction can hit multiple rules.

## Output

Per transaction:
```python
{
  "tx_id": "...",
  "flags": ["round_outflow", "new_vendor"],
  "severity": "low" | "medium" | "high",
  "rationale": "...",
}
```

## Severity calibration

- **low** — single flag, amount < $500. Log to `workspace/anomalies/YYYY-MM.md`, do not escalate.
- **medium** — two flags OR amount $500-$5000. Note in daily inbox summary to CoS.
- **high** — three+ flags OR amount > $5000 OR velocity spike. Immediate escalation.

## What this skill does NOT do

- Does not block the categorization (categorizer runs independently).
- Does not block the QBO write (a flagged tx is still posted; the flag is a *review* signal, not a *stop* signal).
- Does not identify fraud — only signals. Determination is human.
