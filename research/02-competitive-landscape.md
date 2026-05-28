I have enough data. Let me write the report.

# AI Bookkeeping Landscape - May 2026

## 1-2. Active Survivors

- **Pilot** ([pilot.com/pricing](https://pilot.com/pricing)) — Hybrid AI + CPA model. Feb 2026 launched "fully autonomous AI accountant" tier but kept human review for material judgments. $99/mo Essentials, $499/mo Core, $1,500+/mo Custom. Customer: startups/SMB.
- **Digits** ([accountingtoday.com](https://www.accountingtoday.com/news/digits-announces-autonomous-general-ledger)) — Autonomous General Ledger (AGL) + three named agents (Bookkeeping, Finance, Reporting). Claims 95% auto-booking, "outperforms human bookkeepers." Customer: startups, accounting firms.
- **Puzzle.io** ([puzzle.io](https://puzzle.io/blog/puzzle-raises-an-additional-30m-to-fuel-a-new-era-of-ai-powered-accounting)) — $66.5M raised. 85-95% auto-categorization, simultaneous cash + accrual books, deep Stripe/Brex/Ramp/Mercury integrations. Customer: VC-backed startups.
- **Black Ore** ([blackore.ai](https://blackore.ai/post/black-ore-launches-tax-autopilot-for-broad-availability)) — $60M a16z/Oak HC/FT. Tax Autopilot, not bookkeeping. 40% of Top-20 CPA firms onboarded. Enterprise/large CPA firms.
- **Truewind** (YC W23, $17.5M) — AI + concierge service. ~100 customers, including EisnerAmper. Startup/SMB.
- **Ramp Accounting Agent** ([prnewswire.com](https://www.prnewswire.com/news-releases/ramp-launches-accounting-agent-to-automate-bookkeeping-with-real-time-close-302686214.html)) — Auto-codes GL/department/class/location, 3.5x more auto-coding than legacy, 90%+ accuracy. Bolted onto spend platform.
- **Brex** ([brex.com](https://www.brex.com/journal/press/brex-launches-ai-native-accounting-api)) — AI-native Accounting API, accruals automation, ERP sync.
- **Pleo** — Europe leader (25k+ companies). OCR + auto-VAT + sync to Xero/Sage/QuickBooks. Not full bookkeeping — expense layer.
- **Zeni** — AI Accountant Agent with in-house finance team reviewing for GAAP.

## 3. 2025-2026 New Entrants (YC + agentic)
- **Mesh** (YC) — fully AI-native bookkeeping, chat-with-your-books ([ycombinator.com](https://www.ycombinator.com/companies/mesh-2))
- **Beluga Labs** (YC S25) — bookkeeping for creators
- **Cranston AI** (YC F25) — agentic bookkeeping
- **Cactus, Combinely, Hemut** (YC S25) — back-office accounting agents
- YC W26: ~50% of batch is AI agents; back-office is a top vertical ([pitchbook.com](https://pitchbook.com/news/articles/y-combinator-is-going-all-in-on-ai-agents-making-up-nearly-50-of-latest-batch))

## 4. Failures
- **Bench** ([techcrunch.com](https://techcrunch.com/2025/02/05/bench-burned-through-135-million-before-shutting-down/)) — Burned $135M, shut down Dec 27, 2024; Employer.com bought it 72 hours later; 85% of customers stayed. Lesson: human-heavy ops + flat SMB pricing = no path to profit.
- **Botkeeper** ([cpapracticeadvisor.com](https://www.cpapracticeadvisor.com/2026/02/09/botkeeper-is-closing-its-doors/177677/)) — Shut down Feb 7-8, 2026 despite 98% accuracy / 80%+ auto-coding. Killed by client consolidation + cost of large offshore human team. Same lesson as Bench.

## 5. Human-in-the-Loop Consensus
Universal in 2026: agents auto-code 80-95%, humans review material judgments and sign off for SOC 2 / GAAP. "The agent did it" is not auditor-acceptable — reasoning traces required ([beancount.io](https://beancount.io/blog/2026/05/10/agentic-ai-bookkeeping-2026-autonomous-finance-agents-month-end-close-ap-reconciliation-workflows-guide)). Pilot's "fully autonomous" tier (Feb 2026) is the first credible push past this, but still escalates judgment calls.

## 6. Pricing
Flat $/month tiered by company size/transaction volume dominates (Pilot $99-$1,500+, Puzzle similar). Nobody won with %-of-revenue or per-transaction. Spend platforms (Ramp/Brex) bundle accounting free with card volume.

## 7. Best-Practice Consensus
**Agent-first, human-escalated, fully auditable.** Auto-code the 85-95%; pause for material/judgment items; produce a reasoning trace per decision; keep a named human accountable for sign-off. Pure-autonomous is being tested by Pilot but not the consensus. Pure-human-heavy (Bench/Botkeeper) is dead.

## 8. Open Source to Mine
- **OpenAccountants** ([github.com/openaccountants](https://github.com/openaccountants/openaccountants)) — 133 countries, MCP-connectable, accountant-verified skills. Strongest reference.
- **TaxHacker** ([github.com/vas3k/TaxHacker](https://github.com/vas3k/TaxHacker)) — Self-hosted, BYO-LLM, receipts/invoices/statements.
- **ClawKeeper** ([github.com/Alexi5000/ClawKeeper](https://github.com/Alexi5000/ClawKeeper)) — OpenClaw-native, 110 agents, approval-gated execution, tenant isolation. Directly relevant to John's stack.
- **Accountant24**, **Isabella**, **panaversity/accounts_ai** — smaller reference implementations.

## Takeaways for Bookie
1. Don't repeat Bench/Botkeeper: keep human ops thin or zero — sell software margins, not labor.
2. Match the survivor pattern: 85-95% auto-code + escalation + reasoning trace + named human signer.
3. Mine **ClawKeeper** for OpenClaw-native architecture, **OpenAccountants** for the accounting skill taxonomy.
4. Flat tiered $/mo pricing is the only model that has worked.
5. Differentiation gap: most current tools target US startups on Stripe/Brex/Ramp; mid-market and non-US/multi-entity are under-served.

Sources:
- [Pilot pricing](https://pilot.com/pricing)
- [Pilot launches fully autonomous AI bookkeeper - Accounting Today](https://www.accountingtoday.com/news/pilot-launches-fully-autonomous-ai-bookkeeper)
- [Bench burned through $135M - TechCrunch](https://techcrunch.com/2025/02/05/bench-burned-through-135-million-before-shutting-down/)
- [Employer.com acquires Bench - CPA Practice Advisor](https://www.cpapracticeadvisor.com/2024/12/30/employer-com-set-to-acquire-bench-accounting/153755/)
- [Botkeeper is Closing Its Doors - CPA Practice Advisor](https://www.cpapracticeadvisor.com/2026/02/09/botkeeper-is-closing-its-doors/177677/)
- [Why Botkeeper went out of business - CFO Brew](https://www.cfobrew.com/stories/2026/02/17/botkeeper-what-went-wrong)
- [Digits Autonomous General Ledger](https://www.accountingtoday.com/news/digits-announces-autonomous-general-ledger)
- [Digits AI Agents launch](https://finance.yahoo.com/news/digits-launches-first-ai-agents-140000473.html)
- [Puzzle $30M raise](https://puzzle.io/blog/puzzle-raises-an-additional-30m-to-fuel-a-new-era-of-ai-powered-accounting)
- [Black Ore Tax Autopilot GA](https://blackore.ai/post/black-ore-launches-tax-autopilot-for-broad-availability)
- [Truewind YC profile](https://www.ycombinator.com/companies/truewind)
- [Ramp Accounting Agent launch](https://www.prnewswire.com/news-releases/ramp-launches-accounting-agent-to-automate-bookkeeping-with-real-time-close-302686214.html)
- [Brex AI-native Accounting API](https://www.brex.com/journal/press/brex-launches-ai-native-accounting-api)
- [Mesh - YC](https://www.ycombinator.com/companies/mesh-2)
- [YC going all-in on AI agents - PitchBook](https://pitchbook.com/news/articles/y-combinator-is-going-all-in-on-ai-agents-making-up-nearly-50-of-latest-batch)
- [Agentic AI in Bookkeeping 2026 - Beancount.io](https://beancount.io/blog/2026/05/10/agentic-ai-bookkeeping-2026-autonomous-finance-agents-month-end-close-ap-reconciliation-workflows-guide)
- [OpenAccountants GitHub](https://github.com/openaccountants/openaccountants)
- [TaxHacker GitHub](https://github.com/vas3k/TaxHacker)
- [ClawKeeper GitHub](https://github.com/Alexi5000/ClawKeeper)
- [Accountant24 GitHub](https://github.com/machulav/accountant24)
- [Lessons from failure of Bench - ICAEW](https://www.icaew.com/insights/viewpoints-on-the-news/2025/apr-2025/cloud-accounting-software-lessons-from-failure-of-bench)
