# Bookie QBO sandbox setup

> This file is generated from `setup-plan.json` by `harness plan sync-doc`. Edit the plan, not this file.

**Critical path:** First light (Bookie reading your books) needs only steps 4 and 5 from John. Steps 9-11 are mine. Steps 6-8 are deferred (browser-automation surface, a later phase).

## Who does what

- **You (John) — actionable now:** Step 4
- **Claude — does these (some blocked until you finish your steps):** Step 9, Step 10, Step 11
- **Deferred (not needed for first light):** Step 6, Step 7, Step 8

## Steps

### Step 1 — Intuit Developer account  [JOHN DOES THIS] ✓ DONE

Signed up at https://developer.intuit.com using john@husband.llc. Builder tier, free.

*Why this is yours and not automatable:* Account creation under John's identity

### Step 2 — Workspace + Bookie app  [JOHN DOES THIS] ✓ DONE

Workspace created in My Hub > Workspaces; app of type 'QuickBooks Online (Accounting)' named Bookie. AppID bb87a65f...

*Why this is yours and not automatable:* Done inside John's authenticated Intuit dashboard

### Step 3 — Development keys saved to laptop  [JOHN DOES THIS] ✓ DONE

Client ID + Secret from Keys & Credentials > Development saved to /home/john/.config/bookie/qbo-credentials.json (0600, gitignored).

*Why this is yours and not automatable:* Keys are read from John's authenticated dashboard

### Step 4 — Add the Development redirect URI (Keys & credentials page)  [JOHN DOES THIS] TODO

COMPLETE STEPS (start to finish, assume nothing):
1. Open a web browser.
2. Go to this URL: https://developer.intuit.com
3. Top-right, click 'Sign In' and sign in with john@husband.llc (the account you made the app under).
4. After signing in, top-right click 'My Hub'.
5. In the My Hub menu click 'Workspaces'.
6. Click your workspace (named 'Bookie').
7. Click your app card (named 'Bookie', AppID starts bb87a65f).
8. You're now on the app. In the LEFT sidebar find the 'Development Settings' group (NOT 'Production Settings'). If it's collapsed, click it to expand.
9. Under Development Settings, click 'Keys & credentials'.
10. On that page you'll see your Client ID and Client Secret near the top. Scroll DOWN on the same page to a section titled 'Redirect URIs'.
11. Click the 'Add URI' button (or the '+' next to Redirect URIs).
12. In the text box type exactly:  http://localhost:8910/qbo-callback   (all lowercase, no spaces, no slash at the end).
13. Click 'Save'. You should see the URI now listed under Redirect URIs.
14. If a 'Reconnect URL' field on the page won't let you Save without a value, type  https://example.com/reconnect  in it and click Save again.
DO NOT use the 'Settings > Redirect URIs' tab — that one is for Production and stays locked (it shows a 'production key requirement' message). The Development one above needs no approval. Verified against current Intuit docs, May 2026.

*Why this is yours and not automatable:* Requires John logged into his Intuit dashboard

### Step 5 — Run OAuth handshake  [JOHN DOES THIS] TODO _(blocked until Step 4 done)_

Run: bash /home/john/repos/Bookie/scripts/qbo-authorize.sh — browser opens, sign in as john@husband.llc, choose the sandbox company, click Authorize. Script writes refresh_token + realm_id to the credentials file.

*Claude can assist:* I can launch the script; the in-browser Intuit sign-in + Authorize click is John's (auth + consent)

*Why this is yours and not automatable:* OAuth consent to grant the app access to QBO data must be John's click, behind his Intuit login + MFA

### Step 6 — Create Bookie bot Intuit user  [DEFERRED] — deferred

Deferred. Needed later for the QBO web-UI automation surface (For Review queue, Bank Rules). Requires account creation + email verification + MFA — John's when we get there.

### Step 7 — Invite bot to QBO company  [DEFERRED] — deferred

Deferred with step 6.

### Step 8 — Capture bot browser session (one-time MFA)  [DEFERRED] — deferred

Deferred with step 6.

### Step 9 — Sanity-check the laptop  [CLAUDE DOES THIS] TODO _(blocked until Step 5 done)_

I run: ls -la /home/john/.config/bookie/ ; bash /home/john/repos/Bookie/bin/bookie self-check

### Step 10 — Ship credentials to the VPS  [CLAUDE DOES THIS] TODO _(blocked until Step 5 done)_

I run: bash /home/john/repos/OpenHarness/deploy/ship-credentials.sh

### Step 11 — Watch Bookie's first inspection tick  [CLAUDE DOES THIS] TODO _(blocked until Step 10 done)_

I run the pull and read inbox/bookie.md to confirm the first-inspection summary landed.

### Step 12 — Build QBO report-pack generation (P&L, Balance Sheet, GL, Trial Balance)  [CLAUDE DOES THIS] ✓ DONE

Research current QBO report API response shapes (never guess), then build bookie/reports.py producing cash-basis P&L, Balance Sheet, General Ledger, Trial Balance for a date range. Tests against captured/mocked QBO JSON. Ready the instant creds land.

### Step 13 — Build Form-1065 Chart-of-Accounts categorization patterns  [CLAUDE DOES THIS] ✓ DONE

Encode the husband-wife LLC / Form-1065 CoA (per-partner equity, draws, contributions; Schedule-C-aligned expense lines) into the categorizer's pattern tables, plus the domain patterns (home office, vehicle, owner draws, mixed personal/business, estimated taxes). Tests.

### Step 14 — Build the QBO Uncategorized-reclassification pipeline (live write)  [CLAUDE DOES THIS] ✓ DONE

Research the QBO Purchase/JournalEntry update shape (SyncToken, sparse update), then implement the live reclassification that today only logs a recommendation — wrapped in policy.guard. Tests against mocked QBO responses. Ready the instant creds land.

### Step 15 — Build the monthly CPA-handoff cleanup checklist logic  [CLAUDE DOES THIS] ✓ DONE

Implement the monthly cleanup pass (zero out Uncategorized/Ask-My-Accountant, reclassify owner draws to equity, flag personal-in-business, loan interest/principal split, CC-payment netting, 1099 vendor scan) producing a CPA-ready report. Tests.

### Step 16 — Write tests for the browser-automation surface (mocked Stagehand)  [CLAUDE DOES THIS] ✓ DONE

Add tests/test_browser.py exercising TaskBudget hard-stop caps, config loading, is_available() with mocked Stagehand. Behavioral, no live browser. Closes the feature-module coverage gap the goal criterion flags.
