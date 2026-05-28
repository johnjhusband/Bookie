---
name: generate-1099-packet
description: Annual January run. For every vendor paid >= $2,000 in the prior year via non-card methods, generate a 1099-NEC packet for John to file.
user-invocable: false
hidden: false
metadata:
  bookie:
    entry: "bookie.tax.generate_1099_packet"
    requires:
      modules: ["bookie.tax", "bookie.qbo"]
---

# generate-1099-packet

Annual skill. Fires in January per HEARTBEAT.md.

## Threshold (2026 tax year)

- $2,000 paid to a single vendor across the year, by check / ACH / EFT (NOT card — card payments go on 1099-K from the processor)
- Vendor type = contractor / freelancer / non-corporation
- W-9 on file (or escalate to CoS to request one)

## Inputs

- QBO vendor list with YTD totals
- W-9s on file (from QBO Vendor records' "Tax info" panel)
- Payment-method breakdown per vendor

## Output

`workspace/reports/1099-YYYY.md` containing:
- Cover memo: count of forms, total reportable amount
- Per-vendor table: Vendor name, EIN/SSN (from W-9), address, total paid, payment method
- Flagged: vendors paid > $2,000 with NO W-9 on file (CoS escalation: request W-9 before filing)
- Filing deadline reminder: 1099-NEC due to recipients by Jan 31; to IRS by Jan 31 (electronic) or paper Feb 28

## Bookie does NOT file the 1099s

This skill produces the packet. CoS escalates to John for review + filing. Bookie never transmits to the IRS.

## Escalation triggers

- Vendor over threshold with no W-9 → escalate immediately, before John sees the packet
- Vendor name ambiguity (same EIN under two display names) → escalate
- Foreign vendor (potentially needs 1042-S not 1099-NEC) → escalate
