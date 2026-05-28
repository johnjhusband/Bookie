# TOOLS — Bookie

## Python modules (in-process)

| Module | Function | Purpose |
|--------|----------|---------|
| `bookie.categorizer` | `categorize(tx, ...)` | Run the decision chain on one Transaction; pure function, no I/O |
| `bookie.models` | `Transaction`, `Categorization`, `MemorizedRule` | Domain dataclasses |
| `bookie.qbo` | `QBOClient.post_journal_entry(...)`, `fetch_memorized_transactions(...)` | QuickBooks Online REST v3 via OAuth |
| `bookie.plaid_feed` | `PlaidClient.fetch_transactions(...)` | Plaid bank-feed fetcher |
| `bookie.reconciler` | `match_feed_to_ledger(...)` | Bank-feed ↔ ledger matching |
| `bookie.close` | `run_month_end_close(...)` | Monthly close workflow with checkpointing |
| `bookie.cli` | `bookie self-check`, `bookie categorize`, etc. | Operator-facing CLI for ad-hoc work |

## OpenHarness runtime services

| Service | API | Purpose |
|---------|-----|---------|
| `openharness.policy` | `with policy.guard(action):` | Mandatory gate on every state-changing action (QBO writes, payments, JE posts) |
| `openharness.state` | `state.append(...)`, `state.search(...)` | chat.db audit log |
| `openharness.checkpoint` | `checkpoint.save/resume/complete` | Resumable long-running tasks (month-end close) |
| `openharness.agent_loop` | `invoke(provider, ...)` | Daemon-invoked LLM call for narrative work (composing messages, edge-case rationale) |

## External APIs

| Service | Auth | Purpose | Config |
|---------|------|---------|--------|
| QuickBooks Online REST v3 | OAuth 2.0 (intuit-oauth) — refresh token in `config/qbo-credentials.json` | Read CoA, read entities, write Journal Entries, fetch Memorized Transactions | `INTUIT_CLIENT_ID`, `INTUIT_CLIENT_SECRET`, `INTUIT_REFRESH_TOKEN`, `INTUIT_REALM_ID`, `INTUIT_ENVIRONMENT` (sandbox or production) |
| Plaid Transactions API | OAuth (Plaid Link / `access_token` per item) | Pull bank feeds for connected accounts | `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` (sandbox/development/production), per-bank `access_token` in `config/plaid-items.json` |
| Anthropic Claude (via OpenHarness provider) | OAuth via `CLAUDE_CODE_OAUTH_TOKEN` | Edge-case categorization rationale, message composition | Inherited from OpenHarness `auth-profiles.json` |

## OS / CLI binaries on the operating host

| Binary | Purpose |
|--------|---------|
| `python3` | Bookie runtime (>=3.10) |
| `git` | State sync via OpenHarness daemon's git push |
| `claude` | Headless Claude Code invoked by OpenHarness agent_loop |
| `sqlite3` | Debug / ad-hoc query of chat.db |

## Tools I do NOT have (these escalate to Chief of Staff)

- Filing actual tax returns with the IRS / state DORs (never)
- Moving money / paying bills (Bookie does not have payment-rail credentials)
- Signing contracts or agreements
- Creating new QBO companies (one-time setup; CoS handles)
- Modifying Chart of Accounts structure (always escalate; CoA is locked from Bookie's side)

## Web browser

Per Bookie's lessons doc `browser-automation-escalation-ladder.md`, when Bookie needs to interact with a bank portal or vendor site that has no API:

1. Static fetch + parse
2. Lightpanda + Puppeteer/Playwright with selectors
3. Lightpanda + Stagehand (LLM-driven actions)
4. Full Chromium + Stagehand
5. Browserbase (paid)
6. Anthropic Computer Use / OpenAI CUA

Hard stop: 5 min wall clock / 50 LLM calls / $1 cost per task / 10 attempts per site per day. Escalate to CoS on any cap hit.
