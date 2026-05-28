# Browser-automation escalation ladder for Bookie

**Date:** 2026-05-27
**Purpose:** When Bookie needs to interact with a website (bank portal, Quickbooks, vendor invoices, receipts, etc.), pick the cheapest tool that works and escalate on failure. Cache which rung worked for which site so the next visit starts there.

This is the rung selection policy. The hard stop policy at the bottom prevents the CTO-style infinite-retry failure mode.

## The ladder, cheapest to most expensive

### Rung 1 — Static fetch + parse
- **Tools:** `requests` + `beautifulsoup` / `selectolax`, or `lightpanda fetch <url> --dump html` for sites with light JS.
- **Use when:** the data is in the initial HTML response, no login, no JS rendering required.
- **Cost:** microseconds, kilobytes of RAM. Free.
- **Failure signals to escalate:** required content missing from the response, 4xx/5xx, "JavaScript required" page, login wall.

### Rung 2 — Lightpanda + Puppeteer/Playwright with deterministic selectors
- **Tools:** start `lightpanda serve --host 127.0.0.1 --port 9222` once, connect via `chromium.connectOverCDP("ws://127.0.0.1:9222")` or Puppeteer's `puppeteer.connect({ browserWSEndpoint })`.
- **Use when:** the page needs JS to render but selectors are stable and known. Bookie has a recipe for this site from a prior visit.
- **Cost:** ~50-200 ms per action, ~200 MB RAM per browser instance. Free.
- **Failure signals to escalate:** selector miss (element not found), unexpected redirect, layout change broke the flow.

### Rung 3 — Lightpanda + Stagehand (LLM-driven actions)
- **Tools:** same Lightpanda serve, but use Stagehand v3 (CDP-native) and write `page.act("click the submit button")` / `page.extract({ price: "the listed price in USD" })` instead of selectors.
- **Use when:** Rung 2 selectors broke because the site changed; let the LLM find elements at runtime.
- **Cost:** ~1-3s per action (one LLM round-trip per `act`/`extract`). LLM tokens billed per call. Cache the resolved selectors so subsequent runs short-circuit back to Rung 2.
- **Failure signals to escalate:** Stagehand returns "could not find matching element," LLM hallucinates, Lightpanda CDP gap (Stagehand v3 implements features Lightpanda's 17 CDP domains don't cover).

### Rung 4 — Full bundled Chromium + Stagehand
- **Tools:** Playwright's bundled Chromium headless shell + Stagehand. Stop Lightpanda for this task.
- **Use when:** Rung 3 hit a Lightpanda CDP gap; need a real Chromium with the full domain set (network interception, advanced cookies, file uploads with complex MIME, video recording).
- **Cost:** ~170 MB Chromium binary already on disk, ~400 MB RAM at runtime, 2-5s per action. Same LLM cost as Rung 3.
- **Failure signals to escalate:** bot detection triggered (Cloudflare/PerimeterX/DataDome challenge page, CAPTCHA, IP block).

### Rung 5 — Browserbase managed browsers (paid)
- **Tools:** Stagehand pointing at a Browserbase remote browser instead of local Chromium.
- **Use when:** site is actively blocking the local browser (bot fingerprinting, residential IP requirement, geofencing).
- **Cost:** Browserbase pricing (~$0.10–$0.50 per session at time of writing). LLM costs on top.
- **Failure signals to escalate:** even with stealth + residential IPs, the site is unreliable (random captchas, multi-step MFA Bookie can't pass).

### Rung 6 — Anthropic Computer Use / OpenAI CUA
- **Tools:** Claude Computer Use or OpenAI CUA driving a full virtual desktop, clicking by pixel coordinate.
- **Use when:** the site is a React/Canvas/PDF-inside-iframe mess and the DOM doesn't reflect what's on screen, OR Bookie needs to interact with a desktop app, OR the site outright refuses headless browsers.
- **Cost:** LLM tokens for every screenshot + decision (~$1–$5 per multi-step task). Slowest of all rungs (~30-90s per task).
- **Failure signals to give up:** see hard-stop policy below.

## Hard-stop policy

To prevent the CTO-style infinite retry burn:

1. **Per-task time cap: 5 minutes wall-clock.** If a task hasn't succeeded across rungs 1-6 in 5 minutes, surface "manual review needed" to John with a one-line summary of what was tried.
2. **Per-task LLM-call cap: 50 calls across all rungs.** Stagehand + CUA can each generate dozens; cap the total so a runaway loop can't drain credits.
3. **Per-rung retry cap: 2 attempts.** If Rung 3 fails twice, escalate to Rung 4, not retry. Stagehand caching means a successful run shouldn't need retries on the next visit.
4. **Per-site daily attempt cap: 10.** If Bookie has tried the same site 10 times today and still can't get clean data, stop, surface to John, wait for human input. Sites change, banks block scrapers, and infinite retry tells nobody anything new.
5. **Cost ceiling per task: $1.00 LLM/managed-browser spend.** If a task is on track to spend more, stop and surface — likely the wrong abstraction.

When Bookie hits any of those caps, the resulting "manual review needed" must include: the URL, the task (e.g., "fetch last 30 days of transactions"), the rungs attempted, the failure mode at each rung, and Bookie's best guess at why. John reads that, fixes the abstraction or provides a credential, and resumes.

## Caching / site profile

For every site Bookie touches, persist a small site-profile record:

```jsonc
{
  "site": "chase.com/checking",
  "last_successful_rung": 3,
  "stagehand_action_cache": {
    "open transactions tab": "#tx-nav-link",
    "export CSV": "button[data-test='export']"
  },
  "known_blockers": ["mfa-sms"],
  "last_failure": "2026-05-27T18:00:00Z",
  "consecutive_failures": 1
}
```

Next visit:
- Start at `last_successful_rung` (not Rung 1, that almost always fails for chase).
- If `stagehand_action_cache` has the selector for the action, skip the LLM call and use Rung 2 selector directly.
- If `consecutive_failures >= 3`, downgrade `last_successful_rung` by 1 (rung 3 → 4) for the next attempt.

## Why no Playwright-only rung?

Stagehand-on-Chromium and bare-Playwright cover the same browser stack; Stagehand is a strict superset (you can write deterministic selectors AND natural-language actions in the same script). Below Stagehand, Puppeteer is the deterministic-only option, lighter than Stagehand for known recipes. Skip raw Playwright unless a specific Playwright-only feature is needed (mobile emulation, codegen, video recording for human review).

## Why no Browser Use rung?

Browser Use is a competitor to Stagehand — full LLM-driven agent loop. As of May 2026 the consensus is Stagehand has the better abstraction (the four primitives `act`/`extract`/`observe`/`agent` are more composable than Browser Use's task-loop API), but Browser Use is worth re-evaluating in 6 months. Don't add a parallel rung; if Stagehand becomes a problem, swap it for Browser Use at the same position on the ladder.

## Why include CUA at all?

Computer Use is expensive and slow but it works on things nothing else does: PDFs inside Salesforce iframes, banks that lazy-load via Canvas, government portals with image-CAPTCHAs in the workflow. Rare but real. The hard-stop ceiling prevents it from runaway burning budget.

## Reference: tools currently installed on the laptop

- `/home/john/.local/bin/lightpanda` (Ubuntu 24.04 x86_64) — 130 MB, supports `fetch | serve | mcp`.
- Playwright in laptop Python env: needs verification — `python3 -c 'import playwright; print(playwright.__version__)'` to confirm.
- Stagehand: not yet installed. `pip install stagehand` (Python) or `npm i @browserbase/stagehand` (TS) when adopted.
- Browserbase: account signup required, paid.
- Computer Use / CUA: API call only, no install needed beyond Anthropic / OpenAI SDK.

Bookie's install script should provision Rungs 1-4 by default (free, local), and treat Rungs 5-6 as opt-in via env-flag because they have ongoing cost.
