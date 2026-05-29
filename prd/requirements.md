# Bookie — Requirements (traceable)

**Version:** 0.3
**Date:** 2026-05-28
**Status:** Post-re-research, every requirement traced.

Every requirement on this page traces to either (a) John's words, with the quote, or (b) a cited integration contract. Anything that fails the trace test is not here. This is the source of truth; the PRD references this doc, not the other way around.

---

## Who Bookie serves

**John Husband and Tara Husband, dba Husband.LLC.**

- Single entity, single QBO tenant.
- Registered in **Florida** (non-community-property state).
- Per IRS default for state-law LLCs owned by two spouses in non-community-property states: **Form 1065 partnership**. Rev. Proc. 2002-69 disregarded-entity election is unavailable (Florida is not on the 9-state list: AZ, CA, ID, LA, NV, NM, TX, WA, WI). [IRS — Election for Married Couples](https://www.irs.gov/businesses/small-businesses-self-employed/election-for-married-couples-unincorporated-businesses)
- **Cash basis** per John: "Cash."
- No sales tax collected per John: "No."

Source trace:
- Identity, state, basis, sales-tax posture — John (2026-05-28): *"Just John and Tara Husband, LLC dba Husband.LLC ... Florida ... Cash ... No [sales tax]."*
- Form 1065 default — IRS rule [linked above].

---

## R1. Categorize every QBO transaction

**Requirement:** Every transaction that lands in QBO gets categorized to a GL account by Bookie using the decision chain in R2. John never has to look at individual transactions to make this happen.

Source: John (earlier session): *"bookie should autocategorize everything. I don't want to be asked unless it really can't figure it out."*

Source: John (this session): *"I do it. But I'm very bad at it hence the need for you."*

---

## R2. The decision chain

**Requirement:** For each transaction, Bookie runs this chain in order. First match wins.

1. **QBO Memorized / Recurring Transactions** (read-only via API, `RecurringTransaction` entity)
2. **Transaction context** — vendor / memo / amount against the locked Chart of Accounts
3. **Temporal context** — surrounding transactions for transfer-pairs, expense+reimbursement, recurring bills
4. **Historical similarity** — search prior categorizations of the same vendor or pattern
5. **Default categorization** — best-guess GL code tagged low-confidence (Uncategorized Income / Expense / Ask My Accountant)
6. **Escalate to Chief of Staff** — only if the chain itself crashes; never reached in normal flow

Source: John (earlier session): the verbatim chain with priority order.

---

## R3. Inspect QBO on first connection

**Requirement:** The first time Bookie has working QBO credentials (and on a periodic re-check), it pulls the Chart of Accounts, vendor list, last 12 months of posted transactions, and any RecurringTransaction templates. It writes a "what I learned about your books" note to inbox/bookie.md for Chief of Staff review. It uses this to populate its decision chain.

Source: John (2026-05-28): *"The AI can look at the setup when it has access this is a dumb question."*

API: `GET /v3/company/{realmId}/query?query=SELECT * FROM Account|Vendor|Purchase|JournalEntry|RecurringTransaction` per Intuit [Account](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account) / [Vendor](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/vendor) / [Purchase](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/purchase) / [RecurringTransaction](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/recurringtransaction) docs.

---

## R4. Produce reports the CPA can use

**Requirement:** On schedule (monthly + on demand + at year-end), Bookie produces the report set a CPA needs to prepare taxes:

- Profit & Loss, cash basis, with prior-year comparative
- Balance Sheet, cash basis, with prior-year comparative
- General Ledger detail
- Trial Balance
- Vendor list with YTD non-card paid totals (1099 candidates)
- Fixed asset transaction detail
- A/R and A/P aging (even on cash basis — CPA wants visibility)
- Sales Tax Liability sniff test (confirms John's "no" answer is still correct)

These are produced via QBO API report endpoints. CPA gets QBO Accountant access (Bookie posts books cleanly; John invites the CPA via Settings → Manage Users → Accountants).

Source: John (2026-05-28): *"I want it to do my bookkeeping so that I can give the reports to the accountant who will prepare my taxes."*

Source for the specific report list: AICPA Annual Tax Compliance Kit, Form 1065 Short Checklist; reinforced by Xenett / Woodard year-end cleanup checklists.

API endpoints:
- [ProfitAndLoss](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/profitandloss) with `accounting_method=Cash`
- [BalanceSheet](https://developer.intuit.com/app/developer/qbo/docs/workflows/run-reports)
- [GeneralLedger](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/report-entities/generalledger)
- [TrialBalance](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/trialbalance)

---

## R5. Pre-handoff cleanup, monthly

**Requirement:** Each month, before producing reports, Bookie executes the standard CPA pre-handoff cleanup checklist:

| Cleanup | Action |
|---|---|
| Zero out Uncategorized Income / Uncategorized Expense / Ask My Accountant | Recategorize via decision chain; escalate to CoS if chain has no answer |
| Owner draws miscategorized as expense | Move to per-partner Owner's Draw equity accounts |
| Personal expenses through business | Flag for CoS review; do not auto-categorize as deduction |
| Capital vs. expense split | Items > $2,500/each routed to Fixed Assets, not expense |
| W-9 on file for vendors paid > $0 in year (so 1099 calc has the data) | Flag vendors missing W-9 to CoS |
| Bank + CC reconciled with $0 uncleared variance | Browser-driven monthly reconciliation (R7) |
| Loan payments split interest/principal per amortization schedule | Categorize accordingly; escalate to CoS for new loans |
| Credit card payments hit liability (not expensed twice) | Verify via JournalEntry pattern |
| Sales tax liability sniff test | Run report; alert CoS if non-zero |

Source: AICPA + Xenett + Woodard checklists, reinforced by IRS Pub 334 / Pub 463. Item-by-item traceable to professional standards.

---

## R6. CoA structure for Form 1065 partnership

**Requirement:** Bookie's locked Chart of Accounts uses the 1065-partnership structure with per-partner equity accounts:

- **Assets:** Cash, A/R, Undeposited Funds, Fixed Assets, Accumulated Depreciation
- **Liabilities:** A/P, Credit Cards, Sales Tax Payable, Payroll Liabilities, Loans Payable (Current / Long-Term)
- **Equity (per partner):**
  - John Husband Capital
  - John Husband Draws
  - John Husband Contributions
  - Tara Husband Capital
  - Tara Husband Draws
  - Tara Husband Contributions
  - Retained Earnings
- **Income:** Sales/Services, Other Income
- **COGS** (only if inventory)
- **Expenses (Schedule C / 1065 line items):** Advertising, Car & Truck, Commissions/Fees, Contract Labor, Depreciation, Employee Benefits, Insurance, Interest, Legal & Professional, Office Expense, Rent/Lease, Repairs & Maintenance, Supplies, Taxes & Licenses, Travel, Meals (50%), Utilities, Wages, Other

Bookie does not auto-create CoA accounts. It uses what John already has in QBO. If a categorization decision would need a new GL account, it escalates to CoS.

Source: AICPA Form 1065 checklist + Intuit Owner's Draw setup guide.

---

## R7. Browser automation surface (alongside API)

**Requirement:** Bookie drives QBO via REST API where possible and via the QBO web UI where the API has no path. John (2026-05-28): *"the AI should also be able to interact with the software graphically like a human. ... I want the full experience. If the API can't do something I want to have the graphic interface already built and working."*

The 7 documented API gaps Bookie must cover via browser automation:

1. **Initial bank linkage** — when a new bank/account needs connecting (one-time setup; rare). Defer to John in practice.
2. **"For Review" queue read + categorize** — the daily driver when QBO's auto-matcher doesn't fire on Bookie's API-posted Purchase
3. **Force-match** when auto-matcher fails to link a bank-feed line to Bookie's posted Purchase
4. **Bank Rules CRUD** — teach QBO patterns so its own ML categorizer improves and the For-Review queue stays small
5. **Monthly Reconciliation workflow** — match bank statement to cleared transactions
6. **Receipt inbox processing** — OCR-matched receipts attached to transactions (Attachable API handles upload but not the inbox match flow)
7. **Audit Log read** — self-monitoring scrape

Architecture:
- **Stagehand** is the action driver (AI-prompted `act("accept the Notion charge with category Software & SaaS")`). Selector-based Playwright will not survive QBO's monthly UI churn per the research.
- **Local Chromium** is the default browser engine (no Browserbase spend unless needed).
- **Browserbase** is an opt-in config flag for when Akamai pushes back from a VPS IP.
- **Dedicated "Bookie" Intuit user account** invited to John's QBO realm. Audit log will show this bot as the actor, not John. One-time human MFA from the agent's browser profile to trust the device.
- **Human-cadence pacing**: 1-4s jittered between actions.
- **Hard stops**: 5min wall clock / 50 LLM calls / $2 cost / 10 attempts per task per day (per the existing browser-automation escalation ladder in lessons/).

Source: Per Intuit dev community confirmations + Akamai-on-Intuit confirmation + Stagehand docs.

---

## R8. Two-surface decision logic

**Requirement:** For every Bookie action, the daemon picks API or browser based on what each surface can do. The split is documented and not configurable per-call.

| Task | Surface |
|---|---|
| Read CoA, vendors, posted transactions, recurring templates | API |
| POST a new Purchase / Deposit / JournalEntry / Bill / Payment / BillPayment | API |
| Generate P&L, Balance Sheet, GL, Trial Balance reports | API |
| Upload receipt files to a transaction (Attachable) | API |
| Read existing posted transactions for categorizer history | API |
| Write decision rationale to transaction PrivateNote | API |
| **Read "For Review" queue** | Browser |
| **Categorize / accept a "For Review" item** | Browser (when API auto-match doesn't catch up) |
| **Create / edit Bank Rules** | Browser |
| **Monthly Reconciliation** | Browser |
| **Receipt inbox match (after Attachable upload)** | Browser |
| **Read Audit Log** | Browser |
| **Create / edit RecurringTransaction templates** | Browser (read is API; write is UI-only) |

Source: Intuit documentation cited per row.

---

## R9. Cash-basis-specific posture

**Requirement:** Bookie operates in cash-basis mode throughout.

- **Prefer `Purchase` over `Bill` + `BillPayment`.** Bills add AP complexity that cash basis doesn't need. Use `Bill` only if John actually tracks unpaid vendor invoices (he doesn't, per "I'm very bad at it").
- **All reports request `accounting_method=Cash`.**
- **No depreciation booking.** Depreciation is a tax adjustment the CPA layers on at filing; Bookie does not book it. Pub 334 + Agent 3 confirm.
- **Owner draws → per-partner equity accounts**, never payroll. Per Intuit Owner's Draw guide.

Source: John ("Cash") + Intuit cash vs accrual doc + Agent 4 cash-basis specifics.

---

## R10. Domain-specific categorization patterns

These are not features — they are categorization decisions Bookie makes when those patterns appear. Flagged for John's awareness during requirements review:

| Pattern | Bookie's behavior |
|---|---|
| Home office expenses (utilities, internet, rent portions) | Category "Home Office — [utility]"; CPA applies % at tax time |
| Vehicle / fuel through business card | Category "Car & Truck — [subtype]"; CPA chooses standard mileage vs actual at filing. Bookie does NOT track mileage (no GPS). |
| Owner / partner draws to John or Tara personal | Category per-partner Draws (equity), never expense |
| Mixed personal/business charges | Flag for CoS review; do not auto-categorize as deduction |
| Quarterly estimated tax payments out of business account | Category per-partner Draws (equity / tax payment), not expense |
| Credit card payment from checking | JournalEntry netting liability, not duplicate expense |
| Loan payment | Split interest (expense) / principal (liability paydown) per amortization schedule |
| Refund / chargeback / reversal | Match to originating transaction, net to zero |

John (2026-05-28) reviewed and did not veto.

---

## R11. 1099-NEC annual packet (opportunistic)

**Requirement:** At year-end (January), Bookie inspects vendor non-card payment totals. For any vendor over the **2026 threshold of $2,000**, Bookie generates a 1099 packet for CPA filing. If no vendors cross the threshold, Bookie produces no packet and reports "no 1099s required this year" in the year-end summary.

Source: John (2026-05-28): *"I don't know"* about 1099s. Bookie answers it by inspection rather than asking.

Source for threshold: OBBBA raised NEC threshold from $600 → $2,000 for tax year 2026. [OnPay 1099 update](https://onpay.com/insights/1099-reporting-threshold-updates/)

---

## R12. Reporting cadence

**Requirement:** Bookie surfaces work to Chief of Staff (never John) on this cadence:

- **Daily tick (every 60s on the daemon):** silent if there's nothing to report. One-line summary only if For-Review items were processed, or anything escalated.
- **Weekly:** A/R + A/P aging snapshot (so anything that drifts gets caught early), only if non-zero.
- **Monthly (day 1 of new month, for prior month):** P&L + Balance Sheet draft + cleanup-checklist results. CoS reviews; John sees only what CoS escalates.
- **Quarterly (March 1, June 1, Sept 1, Dec 1):** YTD P&L + prior-year comparative + YTD owner draws — what the CPA wants for estimated-tax planning.
- **Annual (January 15 for prior year):** Full CPA package + 1099 packet (if applicable). John invites the CPA via QBO Accountant access.

Source: John ("reports to the accountant") + AICPA mid-year estimate cadence + IRS estimated-tax due dates.

---

## R13. Banned

**Requirement:** Bookie must not implement any of these. They were either invented by me in earlier passes, banned per Chief of Staff rules, or out of scope per John's words.

- **Plaid integration.** QBO has bank feeds. No third-party feed source.
- **Sandbox / dry-run / shadow-mode discipline.** John works on real books from day one.
- **Sales tax tracking as a standing capability.** John doesn't collect sales tax. Only the year-end sniff test remains.
- **AR/AP cadence as a top-level subsystem.** Bookie watches for AR/AP via the standard report set; doesn't manage it as a workflow.
- **Multi-tenant logic.** Single entity.
- **Accrual-basis variants.** Cash only.
- **Notifications to John's phone.** Banned per chief-of-staff-role.
- **A2A2H protocol.** Banned per no-a2a2h-no-pwa.
- **PWA as a UI surface.** Banned per no-a2a2h-no-pwa.
- **Tax planning advice.** Banned per non-CPA bookkeeper legal lane.
- **Investment advice.** Banned per non-CPA bookkeeper legal lane.
- **Filing tax returns.** CPA does this; Bookie produces the package.
- **Signing anything on John's behalf.** Out of scope.
- **Auto-creating GL accounts.** Bookie escalates to CoS for new GL accounts.

---

## R14. Real-world prerequisites for John

These are genuine human-only actions Bookie cannot do. Consolidated in one place.

1. **Intuit Developer account** for the QBO API app credentials. (Already documented; the corrected 5-step setup.)
2. **A dedicated "Bookie" Intuit user account** invited to Husband.LLC's QBO realm with appropriate role (Standard user with All Access, or Company Admin if Bookie needs to manage Bank Rules). The audit log will show Bookie as the actor.
3. **One-time human MFA login** from the agent's browser profile, marking the device trusted. Without this, every browser session triggers MFA challenges.
4. **(Optional, Phase 2) Browserbase account** if local Chromium from the VPS triggers Akamai friction. Not required at start.

That's the entire "you need to do this" list. Everything else is automatable.

---

## R15. Success criteria

Bookie is doing its job when, over a 90-day window:

- **S1.** John spends < 30 min/month thinking about bookkeeping.
- **S2.** The "Uncategorized Income / Uncategorized Expense / Ask My Accountant" buckets are at $0 by month-end.
- **S3.** Monthly P&L + Balance Sheet are produced by day 3 of each month without John lifting a finger.
- **S4.** Bank reconciliation is at $0 uncleared variance by month-end.
- **S5.** At year-end, the CPA accepts the QBO Accountant invite, runs their work, files the return, and asks fewer follow-up questions than the prior year.
- **S6.** Zero notifications pushed to John's phone.
- **S7.** Zero requests from Bookie to John (everything goes through Chief of Staff).
