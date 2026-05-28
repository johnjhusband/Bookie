I have enough material. Let me synthesize the report.

# Bookie Architecture Research — May 2026

## 1. Consensus agent pattern (2026)
**Supervisor-worker graph with typed state + tool-calling**, not ReAct loops. Production financial systems use directed-graph orchestration (LangGraph-style) where a supervisor decomposes goals and dispatches to specialist workers. Reflexion/self-critique loops are out — they're the source of John's "infinite retry" pain. The winning pattern is **plan -&gt; structured tool call -&gt; deterministic verify -&gt; commit**, with bounded execution and no free-running ReAct. Evidence: Digits' Autonomous General Ledger and Puzzle.io both run orchestrator + specialist workers, not monolithic ReAct.

## 2. Verification / accuracy
The 2026 consensus is **probabilistic propose, deterministic decide**: the LLM suggests, a rule engine gates. Concrete patterns in production:
- **Threshold checks** (e.g., any transaction &gt; $2,500 auto-routes to human; new vendor never auto-categorized).
- **Invariants enforced outside the LLM**: debits == credits, trial balance reconciles, sum(splits) == total.
- **Neuro-symbolic fact ledgers** (arxiv 2603.04663) — the LLM cannot write to the ledger directly; a symbolic layer validates first.
- Reported AI categorization accuracy ceilings sit at ~98%, and the remaining 2% is precisely where deterministic gates earn their keep.

## 3. Human-in-the-loop placement
Confidence-thresholded escalation, **not** fixed cadence. Industry convention (Mindra, Digital Applied): financial actions require ~95% confidence to auto-commit; below that, human review. Digits' April 2026 outcome-based pricing only charges when ≥95% of transactions are zero-touch — confirming 95% as the de facto industry bar. Place checkpoints at: new vendor, new GL account, journal entries, anything over a dollar threshold, and month-end close sign-off. Per-transaction review is what Puzzle does; Pilot uses US human reviewers as a backstop layer.

## 4. Audit trail
Required: **append-only immutable log** of (observation, decision rationale, tool call, result, model+prompt version, timestamp). QuickBooks' own Audit Log is the reference UX. EU AI Act high-risk provisions (effective Aug 2026) make explainability + decision logs mandatory for automated financial decisioning. Zero-Trust Agent Identity (ZTAI) — every agent action authenticated and logged independently — is the 2026 standard.

## 5. Idempotency / transactional guarantees
QBO API provides this natively: **Request-Id header** for idempotent creates, and **SyncToken** (version counter on every entity) for optimistic concurrency. Production pattern: idempotency key per tool call, compensating-action registry for every mutation, and deterministic replay from the trace. No two-phase commit with QBO — saga pattern with compensating writes.

## 6. Sandbox / dry-run
Intuit ships a free QBO sandbox company; the standard development practice is dual-mode agents (`--dry-run` emits the planned mutation as JSON without executing). Shadow-mode (agent runs in parallel, writes nothing, diffs against human bookkeeper) is the gold standard before going live.

## 7. Cost control
Three-tier routing: cheap model classifies/categorizes, mid-tier writes journal entries, top-tier only for ambiguous or large-dollar items. **Prompt caching** (Anthropic/OpenAI both offer ~50–90% discount on cached prefix) is mandatory for repeating CoA + vendor lists. Batch the month-end close. Teams report 30–50% cost cuts from routing + caching alone.

## 8. Multi-agent vs monolithic
Field has converged on **supervisor + specialist workers**, but workers are kept narrow (categorizer, reconciler, journal-writer, reporter). The CTO "two-hemisphere" router+executor pattern is correct in spirit but Bookie likely needs 3–5 specialists, not 2. Bigger context windows did not kill multi-agent — they made each worker smarter, not fewer.

## 9. State persistence
**Anthropic shipped persistent memory for Managed Agents (public beta, April 23, 2026)** and "Dreaming" async memory reorg (May 6, 2026). For Bookie specifically: episodic memory (prior categorizations) + semantic memory (this client's CoA, vendor rules) + LangGraph checkpoints for in-flight workflows. Mem0 is the current cross-vendor memory layer. Don't roll your own.

## 10. De facto stack
**LangGraph + Anthropic Claude (Managed Agents w/ persistent memory) + MCP for QBO/Plaid + Mem0 for cross-session memory + Vanta for SOC2 evidence collection.** OpenAI Agents SDK is a viable alternative but LangGraph wins for regulated/financial because of typed state, checkpointing, and explicit HITL interrupt points. Intuit has no first-party agent SDK as of May 2026 — you build on their REST API.

## Sources
- [Agentic AI in Bookkeeping 2026 — Beancount.io](https://beancount.io/blog/2026/05/10/agentic-ai-bookkeeping-2026-autonomous-finance-agents-month-end-close-ap-reconciliation-workflows-guide)
- [Enterprise AI Agent Platforms 2026 — Mindra](https://mindra.co/blog/enterprise-ai-agent-platforms-2026-integration-criteria)
- [Is Your AI Bookkeeper Hallucinating? — BASC](https://bascexpertise.com/is-your-ai-bookkeeper-actually-hallucinating-the-2026-audit-ready-checklist/)
- [Neuro-Symbolic Financial Reasoning (arxiv 2603.04663)](https://arxiv.org/pdf/2603.04663)
- [Puzzle vs Digits — Puzzle.io](https://puzzle.io/blog/puzzle-vs-digits)
- [Agentic Workflow Resilience Audit — Digital Applied](https://www.digitalapplied.com/blog/agentic-workflow-resilience-audit-70-point-checklist-2026)
- [QuickBooks API Developer's Guide 2026 — Zuplo](https://zuplo.com/learning-center/quickbooks-api)
- [MCP Runtime Security for Accounting — Arcade.dev](https://www.arcade.dev/blog/enterprise-mcp-guide-for-accounting-audit-firms/)
- [LLM Cost Control 2026 — First Line Software](https://firstlinesoftware.com/blog/how-to-control-llm-costs-in-production-rate-limits-caching-routing-model-strategy-practical-playbook/)
- [LLM Agent Cost Attribution 2026 — Digital Applied](https://www.digitalapplied.com/blog/llm-agent-cost-attribution-guide-production-2026)
- [State of AI Agent Memory 2026 — Mem0](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [AI Agent Memory 2026 — Digital Applied](https://www.digitalapplied.com/blog/ai-agent-memory-vector-graph-episodic-2026)
- [LangGraph vs OpenAI Assistants 2026 — is4.ai](https://is4.ai/blog/our-blog-1/langgraph-vs-openai-assistants-2026-369)
- [Next-Gen Agentic RAG with LangGraph 2026 — Medium](https://medium.com/@vinodkrane/next-generation-agentic-rag-with-langgraph-2026-edition-d1c4c068d2b8)
