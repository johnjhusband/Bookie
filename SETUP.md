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

IMPORTANT: do NOT use the Settings > Redirect URIs tab — that one is Production-only and stays locked behind app assessment (that's the production-key message you saw). The Development redirect URI lives elsewhere and needs no approval. Steps: (1) My Hub > Workspaces > your workspace > Bookie app. (2) Left nav: expand DEVELOPMENT SETTINGS (not Production Settings). (3) Click Keys & credentials. (4) You'll see Client ID + Client Secret; scroll down to the Redirect URIs section on that same page. (5) Click Add URI. (6) Type http://localhost:8910/qbo-callback (no trailing slash). (7) Save. (8) If a Reconnect URL field on that page blocks Save, put https://example.com/reconnect in it and Save again. ~1-2 minutes. Verified against current Intuit docs May 2026.

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
