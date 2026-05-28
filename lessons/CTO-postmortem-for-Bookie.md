# CTO post-mortem — design inputs for Bookie

**Date:** 2026-05-27
**Status:** CTO v1 sunset. VPS `cto-v1` (Hetzner 130627001) deleted after Hetzner snapshot `391222521`. Public GitHub repos retained at https://github.com/johnjhusband/CTO and https://github.com/johnjhusband/a2a2h .

Bookie is a bookkeeper agent John is building next. This document captures what worked, what didn't, and what design choices to make differently. Read this BEFORE any architecture pass on Bookie.

## What worked

1. **Two-hemisphere split** (OpenClaw left = routing/decisions, Hermes right = execution). When one provider degraded (Hermes' codex-5.5 went `agent_incomplete` for hours), OpenClaw kept producing real artifacts. Single-agent designs would have been dead in the water. Build Bookie with at least one fallback execution path.

2. **Work-pump cron + idle nudge** (every 15m for human-facing pump, every 45m for autonomous cron). Solved "agent goes idle" cleanly. Adaptive cooldown with circuit breaker (`HERMES_WORK_PUMP_RECOVERY_RESTART=0`) stopped the restart-thrash failure mode.

3. **chat.db SQLite as the canonical message bus.** One file, durable, every message persisted with sender/recipient/kind/correlation/content. Powered chat, A2A, audit log, push triggers. Bookie should keep this pattern.

4. **A2A2H maintenance loop with SHA tracker.** The `wiki/A2A2H_LAST_SYNC.md` + per-tick port check successfully kept the extraction repo in sync with the upstream. Two ports landed without intervention. Use the same pattern if Bookie has a sibling repo.

5. **Decision log + backlog JSON + index.md** structure. Made every architectural pivot reviewable. CTO-DECISION-001 through 022 captured the actual reasoning. Bookie should keep this from day one.

6. **GitHub Dependabot + secret scanning + push protection.** Opening Dependabot PRs against a public repo gave us automatic dependency upgrade signals. Pre-commit + pre-push hooks (`scripts/security/git-hooks/`) caught secret leaks. Bookie should enable these on the public repo from day one, not retrofitted.

7. **Real Playwright UI test, not CSS string-match.** When agents claimed "tested" with `unittest` checks that grep'd CSS files for keywords, every PWA chrome regression slipped through. Once a real `tests/test_pwa_chat_first_layout.py` rendered the page at phone viewport and checked actual bounding boxes, agents stopped piling on UI chrome.

## What didn't work / cost real time

1. **Foreground-only PWA on iOS Safari.** Web Push requires standalone PWA mode (Add-to-Home-Screen). John never installed it that way. The push infrastructure (VAPID + pywebpush + FCM endpoint) was complete and tested, but no notification ever reached his phone because iOS refused. **For Bookie: assume the user will not install the PWA. Plan a real outbound channel that works without standalone PWA — Telegram bot is the obvious one (free, no signup beyond `@BotFather`, works without home-screen install).**

2. **Approval packets that never reached John.** Agents wrote "needs John approval" packets into `logs/security/*.md` and never posted to chat.db with `@john`, so no push, no email, no Telegram. John literally could not see them. Five waiting-on-John items sat invisible. **For Bookie: any item that needs the user MUST be posted to the canonical outbound channel as a chat message addressed to them, with a one-liner of what's needed. The markdown packet is the detail backing; the chat ping is the actual ask.**

3. **Misnamed `tail()` chat history function.** Returned messages 1-500 instead of latest 500. On a chat.db with 1500+ rows the PWA always showed days-old history on first load. Reproduced via the live API in 5 minutes once anyone actually loaded the page. **For Bookie: any "show me history" endpoint must have an integration test that loads the API on a populated DB and asserts the response includes the most recent N messages.**

4. **Routine-tick treadmill.** Once the high-priority items were John-blocked, the work-pump fell back to running the same BACKLOG-006 "safe gate pass" check every 15 minutes for 2+ hours straight. 22 of 25 commits in that window were no-op gate ticks. The fix was a directive to skip routine ticks and pick from a specific list of unblocked items, but it should have been a built-in rule from day one. **For Bookie: the work-pump prompt must include "if you've completed a safe-gate check this tick, you must ALSO ship a substantive artifact from the highest unblocked backlog item — a tick that only writes a 'check passed' log is a failed tick." Also: cap consecutive ticks against the same backlog item.**

5. **No automatic test environment on the VPS.** pytest wasn't installed in the default Python; for half the session the agents claimed "37 tests passed" against a suite that never ran. Real testing only happened after manual `pip install --user pytest playwright` + `playwright install chromium`. **For Bookie: the install script must provision the test runner + a real browser the agent can use to verify UI claims. Treat that as a Phase 1 install step, not Phase 4.**

6. **Bookkeeping confusion.** Multiple iterations of "John doesn't mark items resolved" → "Claude Code shouldn't either" → "CTO is the only one who closes backlog." Burned three rounds of memory rewrites. **For Bookie: the canonical bookkeeper (whichever role is named for it) closes items based on observable evidence. The human gives directives, doesn't track status. Establish this rule in the role doc on day one.**

7. **Session context bloat.** Both Hermes and OpenClaw chat sessions accumulated context across days until codex-5.5 started timing out / `surface_error`. Required bounded session ids (`OPENCLAW_SESSION_ID=pwa-john-YYYYMMDD-HHMM` rotated daily). Build session-rotation into the agent's standard pattern, not as a repair.

8. **Cached service worker hell.** PWA cache mismatches between agent and user device were chronic. `SHELL_CACHE` bumped from v3 to v25 across one day with each UI change. The eventual fix was a `/reset` route + a "network-first for shell" SW + an "Update app" button. Even then, John's device showed stale data because the underlying `tail()` was broken (see point 3). **For Bookie: if the user has a client (web/mobile), build the "force latest" route + the network-first SW from day one. Test cache invalidation BEFORE shipping any UI iteration.**

9. **`tail()` function semantics — and "tested" without rendering.** Both came from the same root cause: tests that don't exercise the actual user journey. The "test" was structural ("the SQL query exists", "the CSS class is defined") instead of behavioral ("when a user loads the page they see the latest messages"). **For Bookie: testing rule from the founding doc is `tests must mimic the user's actual flow. Structural assertions don't count as tests for user-facing surfaces.`**

## Critical design choices to make differently for Bookie

1. **Outbound channel before anything else.** Pick Telegram (or whatever John has on his phone right now) as the primary channel BEFORE deploying any service. The PWA is a secondary surface, not the only one.

2. **Bookie has ONE clear job (bookkeeping) and a strict scope.** CTO tried to do research, security, evolution, comms, install reproducibility all at once. Bookie should do bookkeeping for John's businesses end-to-end and not start expanding scope until the core is rock-solid.

3. **Start with a minimal install script that REALLY produces a working agent.** CTO's clone-test-replace candidates failed install ~5 times in a row before giving up. The install script and the running deployment had drifted apart. Bookie's install script must be the ONE source of truth, used by both first-deploy and clone-test. Re-test it from scratch on a fresh VPS every time it changes.

4. **Status-update channel is push-based, not pull-based.** John should never have to open a PWA to see what the agent did. Daily summary goes to Telegram/email automatically. Critical asks ping immediately with the actual question + how to answer.

5. **No "approval packet" pattern unless the user already has a way to see it.** If the agent needs human approval, that's a chat message + push notification with a one-line ask and an inline "reply yes/no" affordance. Markdown in `logs/security/` is the backing detail, not the ask.

6. **Test the user journey, not the code structure.** Founding test rule on day one.

7. **Don't ship features the user hasn't asked for.** CTO accumulated feature-panel chrome (4 cards + release notes + status banners) that buried the actual chat. Bookie ships a chat-first or task-first UI. New features are opt-in, hidden in a settings disclosure by default.

## Hetzner / infrastructure pattern that worked

- Cheap cx43 VPS (€18/mo, plenty for an agent)
- Caddy reverse proxy with auto-TLS for the public surface
- Loopback-only bindings for all internal services (OpenClaw gateway 18789, PWA backend 8088, Hermes 8642/8643, A2A registry 9000)
- All systemd `--user` services, no root
- `git credential.helper=store` from `GITHUB_TOKEN` for autonomous git push
- A pre-commit + pre-push hook to catch accidental secret leaks

Snapshot reference for full state recovery: image `391222521` ("cto-v1 final snapshot before delete 2026-05-27").

## Files captured for Bookie research (in this folder)

- `chat/chat.db` — full 1672-message chat history from the CTO session. Useful for studying agent failure modes, John's actual usage patterns, and what successful chat exchanges looked like.
- `configs/env.template.txt` — 14 environment variables CTO used (names only, values redacted).
- `configs/systemd-user-units/` — systemd unit drop-ins for the 5 services. Direct templates for Bookie.
- `configs/hermes-cron-jobs.json` — Hermes scheduler state, work-pump + daily-sync-audit cron configurations.
- `configs/openclaw.json.head` — first 50 lines of OpenClaw config, shows the agent/skills wiring pattern.

GitHub repos that remain available:
- https://github.com/johnjhusband/CTO (public, full CTO codebase + all logs)
- https://github.com/johnjhusband/a2a2h (public, extracted chat-bridge subset)

Bookie should reference these directly rather than re-derive from scratch.
