# Bookie design-research synthesis

**Date:** 2026-05-27
**Status:** Pre-build research. CTO v1 sunset; this is the design input for Bookie v1.
**Sibling docs in this folder:** `CTO-postmortem-for-Bookie.md`, `browser-automation-escalation-ladder.md`.

Bookie is an autonomous AI bookkeeper for John's businesses. This doc consolidates five parallel research streams (QuickBooks API, competitive landscape, bookkeeping workflow domain, financial-AI agent architecture, US compliance) into one set of design inputs.

The pattern: each section gives the consensus finding, the load-bearing details, and what Bookie must do differently from CTO.

---

## 1. Scope and starting wedge

The 2026 industry consensus, plus Bookie's own constraint that it has to work end-to-end for one user before expanding, narrows the v1 wedge sharply.

**Start here, in priority order:**
1. **Transaction categorization** — locked chart of accounts + per-vendor rules. Highest volume, highest ROI, where AI accuracy ceilings (~98%) are real.
2. **Bank reconciliation** — match feed → ledger. Deterministic logic with AI suggestions for the unmatched tail.
3. **AR/AP cadence** — invoice sends, payment matches, vendor bill capture.
4. **Sales tax (nexus tracking)** — alert before filings due, draft the return; never submit without John's sign-off.
5. **1099-NEC** ($2,000 threshold for 2026) — vendor tracking, year-end packet for John's CPA.
6. **Month-end close orchestrator** — chained workflow, not a single agent loop.
7. **CPA year-end package** — clean trial balance + supporting docs in the format John's CPA wants.

**Do not start with:** tax-planning advice, investment commentary, payroll filings, anything Bookie would have to sign for. Those are out-of-scope for v1 (see Section 7).

---

## 2. Agent architecture

The 2026 consensus on production financial AI agents (Digits' Autonomous General Ledger, Puzzle.io, Truewind, Ramp Accounting Agent) has converged on a single pattern. CTO's two-hemisphere split (router/executor) was directionally right but the wrong granularity for bookkeeping work.

**Pattern: supervisor + 3-5 narrow specialists, typed-state graph, no ReAct.**

- **Supervisor** decomposes the goal ("close April books") into discrete steps and dispatches.
- **Specialists** (narrow, replaceable): `categorizer`, `reconciler`, `journal-writer`, `reporter`, optional `tax-prep-helper`.
- **Orchestration:** LangGraph-style directed graph with typed state and explicit checkpoints. NOT ReAct/Reflexion loops — that pattern is the source of CTO's infinite-retry pain.
- **Execution model:** plan → structured tool call → deterministic verify → commit. Bounded.

**Why not monolithic:** bigger context windows did not kill multi-agent; they made each specialist smarter, not fewer.

**Why not just two hemispheres:** bookkeeping has more independent verbs than "decide vs execute." Categorize, reconcile, write JE, report, escalate — each gets its own narrow specialist with its own tool set and its own success criteria.

---

## 3. The decide-vs-propose split (probabilistic propose, deterministic decide)

This is the single most load-bearing pattern across all five research streams.

**Rule:** The LLM proposes. A rule engine decides. The LLM never writes to the ledger directly.

Concrete implementation:
- **Confidence-thresholded escalation.** Industry de facto bar: ~95% confidence to auto-commit; below that, human-in-the-loop. Digits' April 2026 outcome-based pricing only charges on transactions that go zero-touch — confirming 95% as the live bar.
- **Invariants enforced outside the LLM.** debits == credits. Trial balance reconciles. sum(splits) == total. Period close not allowed to skip a day. These get enforced by deterministic code that the LLM cannot route around.
- **Threshold checks at the gateway:**
  - Any transaction > $2,500 → human review.
  - New vendor → never auto-categorize on first sight; needs human confirm or a rule.
  - New GL account → always human.
  - Any journal entry → always human in v1.
  - Anything outside the locked chart of accounts → human.
- **Neuro-symbolic ledger interface.** A symbolic layer between Bookie and QBO validates every write before it's allowed through.

Reported ML categorization accuracy ceilings sit around 98%. The remaining 2% is precisely where deterministic gates earn their keep — and where CTO's "agent says it tested" failures lived.

---

## 4. QuickBooks integration

**API surface:**
- **REST v3** + **OAuth 2.0** (Intuit's only supported auth path).
- **Refresh tokens:** 5-year cap as of Nov 2025. Bookie must auto-renew before expiry — that's a calendar event in the project from day one.
- **Webhooks:** moving to CloudEvents format with **May 15, 2026 deadline**. Bookie ships with CloudEvents native; do not implement the legacy format.
- **Idempotency built-in:** every create accepts a `Request-Id` header. Use a per-tool-call idempotency key, persisted to disk before the API call fires.
- **Optimistic concurrency:** every entity carries `SyncToken` (version counter). Stale-write attempts fail loudly — handle the conflict, don't retry blind.
- **No two-phase commit.** Use the saga pattern: every mutation registers a compensating action; on failure, replay the compensation chain in reverse.

**Dev environment:**
- **Sandbox company:** Intuit provides free QBO sandbox. Bookie's install script provisions a sandbox tenant by default.
- **Dry-run mode:** `--dry-run` emits the planned mutation as JSON without executing. Required for v1.
- **Shadow mode:** Bookie runs alongside a human bookkeeper for the first month, writes nothing, diffs against human output. This is the gold standard before going live and the cheapest insurance available.

**Cost:** Builder tier of the Intuit App Partner Program is likely free at our scale. Platinum tier sits at ~$0.25 per 1,000 read calls. Even an aggressive automation loop is < $5/mo in API calls.

**SDK:** Python — `intuit-oauth` + `python-quickbooks`. Both are first-party-supported, maintained, no need to wrap REST by hand.

**Strategic note:** Intuit + Anthropic partnership launched spring 2026 with Claude Agent SDK on Intuit's hosted platform. Worth evaluating in Phase 2 once Bookie is shipping — could collapse some of the integration surface. Do not depend on it for v1.

---

## 5. Competitive landscape (what to copy, what to avoid)

**The graveyard:**
- **Bench** ($135M raised) shut down Dec 2024. Heavy human-ops costs, US bookkeepers on payroll, never automated past ~60%.
- **Botkeeper** shut down Feb 2026. Same story — couldn't make the unit economics work when humans had to touch every book.

**The survivors and what they do right:**
- **Digits** — Autonomous General Ledger. 95%+ auto-coding. Outcome-based pricing. Reasoning trace exposed in UI ("I categorized this $342 charge as 'Software' because vendor=Notion and amount fits subscription pattern").
- **Puzzle.io** ($66.5M raised) — strong UX layer, multi-agent backend, per-transaction human review built into the workflow.
- **Pilot** ($99-1,500/mo) — US human reviewers as the backstop layer. Slower, but client trust is higher.
- **Truewind / Ramp Accounting Agent / Brex** — embedded inside an existing financial product; the agent isn't the product, the workbench is.

**Open-source reference: `ClawKeeper`** (github.com/Alexi5000/ClawKeeper). OpenClaw-native, 110 agents already wired up. Worth reading even if Bookie doesn't use OpenClaw. Specifically: how they segment specialist roles, how they handle the human-approval gate, how they record audit trail.

**The pattern that works in 2026:**
1. 85-95% auto-code by the agent.
2. Named human signer for anything that touches money, taxes, or third parties.
3. Reasoning trace exposed to the user, every transaction.
4. Outcome-based pricing (only charge on zero-touch txns) keeps incentives aligned.

**What kills these companies:** heavy human-ops costs. Bookie's design must keep humans (John) on the *approval* path, not the *production* path. The moment a human has to touch a transaction to make it ship, the unit economics break.

---

## 6. Workflow / domain (what bookkeeping actually IS)

The day-to-day rhythm of bookkeeping is unromantic and chunked. Knowing the cadence determines what Bookie automates and what's a notification.

**Cadence:**
- Daily: 0-30 min of categorization + reconciliation pickups (mostly automation; humans review only escalations).
- Weekly: 1-2 hours of vendor bill capture, AR follow-up, sales tax pacing.
- Monthly: 2-3 hours of close work — accruals, prepaids, depreciation, intercompany.
- Quarterly: sales tax filings (state-by-state), estimated taxes, owner draws review.
- Annual: 1099s (Jan 31), W-2s (if payroll), CPA package, year-end accruals.

**Key concepts Bookie must encode:**
- **Locked chart of accounts.** New GL account = human approval, every time. CoA drift is the #1 cause of close errors.
- **Cash vs accrual.** John's businesses likely use cash basis for tax, accrual for management. Bookie should support both and switch at report time, not at entry time.
- **Materiality threshold.** $50 is noise. $5,000 is material. Bookie uses materiality to decide what to investigate vs let pass.
- **Fraud sniff tests.** Round numbers, unfamiliar vendors, after-hours card activity, duplicate amounts. These are pattern-match rules, not AI judgment.
- **Sales tax nexus.** Crosses state thresholds → registration required. Bookie tracks state-by-state cumulative sales and alerts before nexus triggers.
- **1099-NEC threshold $2,000** for 2026 tax year (changed from $600). Track vendors all year, packet in January.

**Close timeline (the deliverable for the month):**
- Day 1-3: accruals, prepaids, depreciation calculated and posted.
- Day 4-5: bank/credit card recs done.
- Day 5-7: trial balance reviewed by John; close locked.
- Human bookkeeper close: 5-7 days. AI-assisted close: 3-4 days. Bookie v1 target: 4-day close for John's businesses.

**Common screw-ups Bookie must guard against:**
- Sales tax filing missed → state penalty + interest.
- 1099 missed → IRS penalty per form.
- Owner draws miscategorized as expenses → wrong taxable income.
- Mixed personal/business charges → not Bookie's job to clean; flag and route to John.
- Credit card statement reconciliation off-by-one → catches itself via deterministic invariant.

**CPA handoff (annual):**
- Trial balance + general ledger + bank/cc reconciliations + fixed asset schedule + accruals schedule + 1099 list + sales tax filings list.
- In whatever format John's CPA wants (probably QBO Accountant access). Don't reinvent the package.

---

## 7. Compliance / regulatory

This is the section where "Bookie does it for me" and "Bookie does it for a customer" diverge sharply.

**Self-use (John's own businesses): minimal formal compliance.**

The moment Bookie touches anyone else's books, John becomes a **GLBA "financial institution"** under FTC Safeguards Rule (16 CFR 314). The rules get sharp fast. Treat v1 as self-use only; revisit before taking on any external client.

**Non-negotiables even for self-use:**
1. **OAuth-only bank connections.** No password storage. Use **Plaid** (preferred) or **MX** — both SOC 2 + ISO 27001, OAuth-first, cover ~90% of US banks via OAuth. Avoid **Yodlee** for new builds.
2. **AES-256 at rest, TLS 1.2+ in transit.** Standard, no exceptions.
3. **MFA on every system** that touches financial data. Bookie's web UI, Bookie's admin shell, the laptop that holds the bank token cache.
4. **Tamper-evident audit log, 7-year retention.** Append-only, timestamped, hash-chained or WORM. Captures who/what/when/why for every Bookie action.
5. **Human-approval gate on every write** to QBO, every tax filing, every payment. Always. v1 has no exceptions.
6. **No investment advice. No income-tax-planning advice.** Bookie describes what the data shows. It does not prescribe what John should do. This is the line between bookkeeping (no license) and tax/investment advice (CPA/EA/RIA territory).

**Records retention:**
- IRS Topic 305: 3-year baseline.
- 7 years for bad debt, worthless securities, or under-reporting > 25%.
- Employment tax: 4 years.
- Payroll: 4+ years.
- **Default to 7 years for everything.** Storage is cheap. State variation (CA FTB: 4 years minimum, often longer in practice) is covered by the 7-year default.

**AI-specific 2025-26 regulations:**
- **California SB 53** (Frontier AI, eff Jan 1 2026) — applies to frontier-model developers, not Bookie.
- **California CCPA ADMT regs** (eff Jan 1 2026) — financial-services automated decisions on California consumers need pre-use notice + opt-out + risk assessment. Triggers if Bookie ever services a CA customer.
- **California AB 316** — kills the "the AI did it" defense. Owner is liable.
- **NYDFS AI cybersecurity guidance** (May 2026) — applies to NY-licensed entities only.
- **EU AI Act** — irrelevant unless serving EU users.
- **FTC** actively enforcing on AI misrepresentation — don't claim Bookie is a CPA, don't claim it guarantees compliance.

**If Bookie ever takes a paying client:**
- SOC 2 Type II is table stakes.
- ISO 27001 + ISO 42001 (AI management system) are 2026 buyer asks.
- Under 5,000 consumers = exempt from written risk assessment/pen-test/IR plan under Safeguards Rule, but **not** exempt from encryption/MFA/access controls.
- E&O / cyber liability insurance ($1-2M) the day a client signs.

**Boundaries that are NOT bookkeeping:**
- Signing tax returns (Circular 230, needs PTIN/EA/CPA/attorney).
- Representing John to the IRS (same).
- Giving income-tax-planning advice (same).
- Giving investment advice for compensation (RIA registration).

**Stay descriptive ("here's what your data shows"), not prescriptive ("you should deduct X").** This is the legal line.

---

## 8. Audit trail / verification / state

**Audit log structure** (required by IRS, by EU AI Act high-risk provisions effective Aug 2026, by every SOC 2 audit, and by John's own debugging needs):

Each row captures: `(observation, decision_rationale, tool_call, result, model_version, prompt_version, timestamp, idempotency_key)`. Append-only. Hash-chained or stored in WORM. Retained 7 years.

QuickBooks' own Audit Log is the reference UX — Bookie should produce something John could open in QBO's Audit Log view and recognize.

**State persistence patterns (2026):**
- **Episodic memory:** prior categorizations, prior reconciliation pairs. Built on Anthropic Managed Agents persistent memory (public beta April 23, 2026) or Mem0.
- **Semantic memory:** this entity's locked CoA, vendor rules, materiality threshold, fiscal year.
- **Procedural memory:** workflow checkpoints from LangGraph. Mid-close interruption resumes cleanly.

**Don't roll your own memory layer.** Mem0 is the cross-vendor abstraction; Anthropic Managed Agents is the platform-native option. Both work; pick one early.

---

## 9. Cost control

CTO had no cost ceiling and burned tokens on routine ticks. Bookie's cost rules from day one:

1. **Three-tier model routing:**
   - Cheap model (Haiku-equivalent) categorizes and classifies.
   - Mid-tier (Sonnet-equivalent) writes journal entries and drafts reports.
   - Top-tier (Opus-equivalent) only for ambiguous calls, large-dollar items, or month-end synthesis.
2. **Prompt caching mandatory.** Repeating CoA + vendor lists in every prompt = cache them. Anthropic/OpenAI both offer ~50-90% discount on cached prefixes.
3. **Batch the month-end close.** Don't run agents continuously through the month; trigger on bank-feed updates and a once-daily sweep.
4. **Hard cost caps per task** (same pattern as the browser-automation ladder hard-stop policy):
   - Per-task LLM call cap (e.g., 20 calls for a single transaction categorization).
   - Per-day token budget (e.g., $1/day for self-use; surface to John before exceeding).
   - No retries on tool failure beyond 2 attempts — escalate, don't burn.

Teams report 30-50% cost reductions from routing + caching alone vs. naive single-model loops.

---

## 10. Sandbox / dry-run / shadow mode

CTO never had a working test environment until the session was 80% over. Bookie's install script must provision:

1. **QBO sandbox tenant** by default (Intuit provides free).
2. **Dry-run mode** — every mutation has a `--dry-run` flag that emits the planned API call as JSON without executing. Default for the first week of any new specialist.
3. **Shadow mode for v1 cutover** — Bookie runs in parallel with the human bookkeeper (or with John doing manual books) for a calendar month. Bookie writes nothing to production QBO; instead it writes proposed JEs to a parallel ledger. Daily diff report. Only after diffs are < 2% material does Bookie get write access to production.

This is the single biggest insurance policy against the CTO failure mode of "the agent says it tested."

---

## 11. Outbound channel (the lesson CTO most badly failed)

From the CTO postmortem (see sibling doc): **the PWA-only outbound channel was the project's worst design choice.** John never installed it as standalone; no push notification ever reached his phone; approval packets sat invisible.

**Bookie's outbound channel rules:**
1. **Telegram first.** Free, no signup beyond `@BotFather`, works on phone without standalone-PWA mode, supports inline buttons for yes/no approvals.
2. **Daily summary pushed automatically** — John never has to open anything to know what Bookie did.
3. **Approvals are chat messages** with one-line context + inline buttons. The full audit packet is a click away but not the ask itself.
4. **Email (Resend) as backup** for items that need a paper trail (tax filings, 1099 packets, year-end reports).
5. **PWA is a secondary surface for browsing history, not the only channel.** Push-first, pull-second.

**Test from day one:** push a fake approval through Telegram, click yes from the phone, verify Bookie acted. If that loop doesn't work, nothing else matters.

---

## 12. Decision summary — what Bookie does differently from CTO

| Concern | CTO did | Bookie does |
|---------|---------|-------------|
| Outbound channel | Foreground PWA only | Telegram + email; PWA secondary |
| Agent topology | 2 hemispheres (router/executor) | Supervisor + 3-5 narrow specialists |
| Loop pattern | ReAct-ish with retries | Plan → tool → verify → commit, bounded |
| Test environment | Provisioned half-way through | Phase 1 install step, mandatory |
| Approval pattern | Markdown packets, invisible | Push notification with inline approve |
| Confidence threshold | Implicit | 95% explicit, < 95% routes to human |
| Cost control | None | 3-tier routing + caching + per-task caps |
| Audit log | Chat.db (good) | Chat.db + append-only verified audit log |
| State | Single growing session | Persistent memory (Anthropic / Mem0) |
| Sandbox | None | QBO sandbox + dry-run + shadow mode |
| Scope | Sprawled (research, security, comms, evolution) | Bookkeeping for John's businesses, end-to-end |
| Backlog closing | Confused | Bookkeeper agent closes based on observable evidence |
| Browser interaction | Ad-hoc | Escalation ladder w/ hard stops (sibling doc) |

---

## 13. Stack (de facto 2026 default for regulated financial agents)

- **Orchestration:** LangGraph (typed state, checkpoints, explicit HITL interrupts). OpenAI Agents SDK viable; LangGraph wins for regulated/financial.
- **Model:** Anthropic Claude (Managed Agents w/ persistent memory, public beta April 23, 2026).
- **Tool layer:** MCP for QBO + Plaid + email + Telegram. Native MCP servers exist for most of these.
- **Memory:** Mem0 for cross-session, LangGraph checkpoints for in-flight workflows.
- **Banking:** Plaid (OAuth, SOC 2 + ISO 27001).
- **Email:** Resend (already chosen during CTO).
- **Audit/compliance evidence:** Vanta if Bookie ever takes a paying client; not needed for self-use.
- **Secrets:** Local HashiCorp Vault or AWS Secrets Manager (envelope encryption for Plaid tokens).
- **Infra:** Hetzner VPS (same pattern that worked for CTO — cx43 €18/mo, Caddy reverse proxy, systemd user services, loopback bindings for internals).

**Don't depend on Intuit's Claude Agent SDK partnership for v1.** Evaluate in Phase 2.

---

## 14. Open questions for John (not asks — flag these for design conversation)

1. **One business or three?** Husband.llc + DFU Mortgages + others? Determines multi-tenant model from day one.
2. **John's CPA — do they want QBO Accountant access or a flat-file year-end packet?** Cheap to ask; expensive to redo.
3. **Cash or accrual basis?** Probably both (cash for tax, accrual for management) but worth confirming.
4. **What does "I want a daily summary" look like?** A Telegram message with N bullet points? An email with a P&L delta?
5. **First-month shadow mode — is John willing to run dual-track books for a calendar month?** This is the single biggest design choice and has a cost.

These are pre-build clarifications, not blockers. List them, don't ship them as asks until John actually wants to talk Bookie design.

---

## 15. Reading list (sources used)

QuickBooks API + dev environment:
- Intuit Developer docs (REST v3, OAuth 2.0, webhooks)
- Zuplo QuickBooks API Developer's Guide 2026
- `python-quickbooks` + `intuit-oauth` SDK docs

Competitive landscape:
- Digits, Puzzle, Pilot, Truewind, Ramp Accounting Agent, Brex product pages
- Bench/Botkeeper postmortems
- ClawKeeper (github.com/Alexi5000/ClawKeeper)

Architecture:
- Beancount.io — Agentic AI in Bookkeeping 2026
- Mindra — Enterprise AI Agent Platforms 2026
- arxiv 2603.04663 — Neuro-Symbolic Financial Reasoning
- Mem0 — State of AI Agent Memory 2026
- is4.ai — LangGraph vs OpenAI Assistants 2026

Compliance:
- FTC Safeguards Rule / GLBA
- IRS Topic 305
- Plaid OAuth + open-finance trust/security docs
- King & Spalding — New California AI laws Jan 1 2026
- NYDFS AI cybersecurity guidance May 2026
- CPA Journal Feb 2026 — Blurring the Lines

Workflow / domain:
- Standard bookkeeping cadence references
- 1099-NEC threshold change to $2,000 for 2026
- State sales-tax nexus tracking
