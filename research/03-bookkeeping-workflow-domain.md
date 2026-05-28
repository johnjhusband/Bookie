I have enough material. Synthesizing the report.

# Bookie Research: Small-Business Bookkeeping, May 2026

## 1. Recurring cadence (1-5 employee LLC, typical hours)
- **Daily/weekly (~1-2 hrs/wk):** categorize bank/credit-card transactions as they sync from Plaid/feeds, send invoices, follow up on overdue AR, enter bills (AP), upload receipts.
- **Monthly (~2-3 hrs):** reconcile every bank, credit-card, and loan account; review AR aging buckets (current/30/60/90+); review AP aging; post accruals/prepaids/depreciation; produce P&amp;L, balance sheet, cash flow statement; verify payroll register.
- **Quarterly:** estimated tax payments (1040-ES for pass-through owners), 941 payroll filings (handled by payroll provider but bookkeeper records), sales tax filings (frequency varies by state).
- **Annually:** 1099-NEC by Feb 2 (2026 deadline shifted from Jan 31), W-2s, year-end close, CPA package.
(Sources: Pilot, QuickBooks, Focus CPA, SDO CPA checklists.)

## 2. Chart of accounts (COA)
The COA is the taxonomy every transaction maps to. It matters because an LLM that picks accounts inconsistently produces a P&amp;L that lies. **The dominant failure mode is consistent-but-wrong:** an AI that miscategorizes "Amazon" purchases (software subscription vs. office supplies vs. capex) propagates the same error across thousands of rows. Other classic LLM pitfalls: confusing owner draws with payroll, expensing capital items (&gt;$2,500) instead of capitalizing, misclassifying COGS as opex, treating loan principal as expense (only interest is). Fix: lock the COA, train rules per vendor, allocate 1-2 weeks of historical cleanup before going live. (Source: Articsledge, Finlens, BooksLA AI-bookkeeping guides 2026.)

## 3. Bank reconciliation
Steps: (a) get statement ending balance + date; (b) confirm all transactions for the period are entered; (c) match each statement line to a ledger entry; (d) investigate uncleared items — deposits in transit and outstanding checks explain most gaps; (e) drive "difference" to $0.00; (f) save the reconciliation report. Today QuickBooks, Xero, Puzzle, Digits auto-suggest matches; humans resolve the residual. (Source: QuickBooks/Intuit reconciliation docs.)

## 4. Month-end close
Order: record all transactions -&gt; reconcile cash &amp; cards -&gt; AR aging -&gt; AP cutoff -&gt; adjusting entries (accruals, prepaids, depreciation, payroll accrual) -&gt; generate financials -&gt; variance review. Target 5-7 business days; AI-automated firms hit 3-4 days. Parallelizable: AR review, AP review, reconciliations of independent accounts. Sequential: adjusting entries must follow reconciliations; financials follow adjusting entries. (Source: HighRadius, Beancount.io, QuickBooks.)

## 5. Sales tax / nexus
Post-Wayfair, every state with sales tax has economic nexus. Common threshold: **$100K revenue OR 200 transactions** in prior 12 months. Outliers: CA/TX ($500K revenue only), NY ($500K + 100 txns). 2026 changes: IL removed 200-txn test 1/1/26; KY removes 8/1/26. Bookie needs per-state rolling sales tracking, marketplace-facilitator carve-outs, and registration triggers. Filing cadence varies (monthly/quarterly/annual) by state and volume. (Sources: TaxCloud, Numeral, Sales Tax Institute 2026 charts.)

## 6. 1099-NEC
$600 threshold for 2025 tax year (filed early 2026); rises to **$2,000 starting 2026 tax year**. Deadline Feb 2, 2026 (Saturday slip). Top mistakes: missing W-9 collected before first payment, wrong TIN/EIN, using non-scannable Copy A printout, filing 1099-MISC instead of NEC, forgetting recipient copy (separate §6722 penalty). Penalties: $60 -&gt; $130 -&gt; $340/form. (Source: Xero, QuickBooks, Alloy Silverstein 2026 guides.)

## 7. CPA year-end handoff
Package: trial balance, general ledger (full transaction detail per account), P&amp;L, balance sheet, cash flow, AR/AP aging, fixed-asset schedule, depreciation schedule, loan amortization schedules, payroll summary, 1099/W-2 copies, bank statements + reconciliations, owner-draw/contribution log, and a memo flagging unresolved items. Books locked after handoff. (Source: Bench, Dean Paley CPA, Wolters Kluwer.)

## 8. Real-world screw-ups
Commingling personal + business (kills LLC liability shield), skipping reconciliations, falling behind on data entry, misclassifying contractors as employees (or vice versa), missing receipts for expenses, not tracking AR -&gt; cash crunch, payroll-tax late deposits (triggers automatic IRS penalties), capitalizing-vs-expensing errors, sales tax not remitted, owner not telling bookkeeper about bonuses/side purchases. (Source: SCORE, Pilot, Bench.)

## 9. Judgment / non-rule knowledge
- **Materiality:** is a $40 misclassification worth fixing? Usually no; a $4,000 one yes. Rule of thumb ~0.5-1% of revenue or 5% of net income.
- **Fraud sniff tests:** duplicate vendor with slightly different name, round-number invoices, vendor address = employee address, expense reports that creep up monthly, checks just under approval thresholds, weekend/holiday entries.
- **Tax-strategy hints:** Section 179 vs. bonus depreciation election, accountable-plan reimbursements, home-office %, S-corp reasonable-comp ratio, retirement-plan contribution timing.
- **Cutoff judgment:** which period does a Dec 30 invoice for January work belong to?
(Source: PCAOB AS 2401, Acuity fraud-prevention guide.)

## 10. Cash vs. accrual
Cash = record when money moves; accrual = record when earned/incurred. Practical LLC reality: most &lt;$25M LLCs **file taxes on cash** (simpler, defers tax) but **manage internally on accrual** if they carry inventory, invoice customers, or want true profitability. IRS requires accrual for inventory businesses unless under the $30M gross-receipts small-taxpayer exception. Bookie must support both, with a switch, and produce a cash-to-accrual reconciliation at year-end for the CPA. (Source: QuickBooks, AccountingTools, Block Advisors.)

## Bookie automation priority (my recommendation)
1. Transaction categorization with locked COA + per-vendor rules (highest volume, highest ROI).
2. Bank/CC reconciliation (rule-based + LLM for the residual).
3. AR invoicing + follow-up (cash-flow critical).
4. AP intake (bill capture, approval, schedule).
5. Sales-tax tracking across states.
6. 1099/W-9 lifecycle (collect at vendor onboarding, not December).
7. Month-end close orchestrator.
8. CPA year-end package generator.
Judgment-heavy items (materiality calls, fraud red flags, tax strategy) keep human-in-loop.

## Sources
- [SDO CPA bookkeeping checklist](https://www.sdocpa.com/bookkeeping-checklist-article/)
- [Pilot bookkeeping checklist](https://pilot.com/blog/bookkeeping-checklist)
- [Focus CPA monthly checklist 2026](https://focuscpa.com/monthly-bookkeeping-checklist-small-business/)
- [HighRadius month-end close](https://www.highradius.com/resources/Blog/what-is-month-end-close-process/)
- [Beancount.io month-end close](https://beancount.io/blog/2026/04/10/month-end-close-process-complete-checklist-for-small-businesses)
- [QuickBooks reconciliation guide](https://quickbooks.intuit.com/r/accounting/bank-reconciliation/)
- [TaxCloud nexus chart 2026](https://taxcloud.com/blog/sales-tax-nexus-by-state/)
- [Numeral economic nexus 2026](https://www.numeral.com/blog/economic-nexus)
- [Sales Tax Institute nexus chart](https://www.salestaxinstitute.com/resources/economic-nexus-state-guide)
- [Alloy Silverstein 1099 deadline 2026](https://alloysilverstein.com/1099-nec-deadline-approaching-what-businesses-need-to-know-for-2026/)
- [Xero 1099 filing guide 2026](https://www.xero.com/us/guides/1099-filing-requirements/)
- [QuickBooks 1099 deadlines](https://quickbooks.intuit.com/r/taxes/1099-deadline/)
- [Articsledge AI bookkeeping 2026](https://www.articsledge.com/post/ai-bookkeeping)
- [Finlens what AI gets wrong](https://www.finlens.app/blogs/ai-bookkeeping-software-guide)
- [Books LA AI bookkeeping 2026](https://www.booksla.com/how-to-use-ai-for-bookkeeping-without-losing-control-2026/)
- [Dean Paley CPA year-end handoff](https://deanpaley.com/preparing-for-year-end-a-bookkeepers-checklist-for-compilation-engagements/)
- [Bench tax-pro FAQ](https://www.bench.co/blog/bookkeeping/faq-for-tax-professionals)
- [Wolters Kluwer general ledger](https://www.wolterskluwer.com/en/expert-insights/maintaining-a-general-ledger)
- [QuickBooks cash vs accrual](https://quickbooks.intuit.com/accounting/cash-vs-accrual-accounting-whats-best-small-business/)
- [AccountingTools LLC accounting](https://www.accountingtools.com/articles/llc-accounting.html)
- [SCORE top 10 bookkeeping mistakes](https://www.score.org/resource/article/top-10-bookkeeping-mistakes-small-businesses)
- [Bench common mistakes](https://www.bench.co/blog/bookkeeping/common-bookkeeping-mistakes)
- [Acuity fraud prevention 2026](https://acuity.co/prevent_bookkeeping_fraud/)
- [PCAOB AS 2401 fraud consideration](https://pcaobus.org/oversight/standards/auditing-standards/details/AS2401)
