# Bookie QBO setup — your active checklist

Keep this file open while you work through the setup. Every URL, every field name, every command is written out. Nothing requires you to scroll up to a previous message.

## Where you are right now

You're partway through Step 4. Your Intuit Developer account is created, your Workspace and Bookie app are created, and your Development Client ID and Client Secret are already saved to `/home/john/.config/bookie/qbo-credentials.json` on your laptop with secure permissions.

You're currently stuck on the Settings → Redirect URIs page in the Intuit Developer dashboard. It shows a message about needing to complete a "production key requirement." That message is misleading. The real gate is that the earlier Settings tabs (Basic app info, App URLs, App terms of service, App categories, Geolocation) aren't filled in yet. Once you save those tabs, the Redirect URIs section unlocks.

Continue from **Step 4** below.

---

## Step 1 — Intuit Developer account (DONE)

You signed up at https://developer.intuit.com using `john@husband.llc`. You're auto-enrolled in the Builder tier of the Intuit App Partner Program (free).

## Step 2 — Workspace and Bookie app (DONE)

You created a Workspace called "Bookie" (or similar) in My Hub → Workspaces, and inside it created an app of type "QuickBooks Online (Accounting)" named "Bookie". The app shows AppID starting with `bb87a65f...`.

## Step 3 — Development keys (DONE)

You navigated to the Bookie app → Keys & Credentials → Development tab, copied the Client ID and Client Secret, and they're saved to `/home/john/.config/bookie/qbo-credentials.json` on your laptop with `0600` permissions. The file is gitignored.

You can verify the file is in place by running:

```bash
ls -la /home/john/.config/bookie/qbo-credentials.json
python3 -c "import json; d=json.load(open('/home/john/.config/bookie/qbo-credentials.json')); print('client_id ok:', bool(d['client_id'])); print('client_secret ok:', bool(d['client_secret']))"
```

You should see the file with `-rw-------` permissions and both fields showing `ok: True`.

## Step 4 — Settings tabs and Redirect URI (CURRENT STEP)

The Settings → Redirect URIs section is gated by the other Settings tabs being incomplete. Walk through these tabs in order in the Intuit dashboard and save each one. The tabs are visible across the top of the Settings page:

### 4a. Basic app info

Fill in:

- **App name:** Bookie
- **App description:** Autonomous bookkeeping for Husband.LLC
- **Support email:** `john@husband.llc`
- **Support phone:** (your phone, or skip if optional)
- **App logo:** optional for Development; required for Production

Click Save.

### 4b. App URLs

Fill in:

- **Host domain:** for Development you can use a placeholder like `example.com` — Intuit accepts placeholders for Development, but Production review will reject anything that isn't a real domain.
- **Launch URL:** `https://example.com/launch` (placeholder for Development)
- **Disconnect URL:** `https://example.com/disconnect` (placeholder for Development)
- **End user license agreement (EULA) URL:** `https://example.com/eula` (placeholder for Development)
- **Privacy policy URL:** `https://example.com/privacy` (placeholder for Development)

Click Save.

### 4c. App terms of service

Read and accept Intuit's Developer Agreement. Click whatever checkbox or "I agree" button is presented. Save.

### 4d. App categories

Pick **Accounting** or **Bookkeeping** from the list. Save.

### 4e. Geolocation (or "Accepted countries")

Select **United States**. Save.

### 4f. Redirect URIs

Now go back to the **Redirect URIs** tab. It should be unlocked.

Make sure the **Development** pill is selected (dark blue with white text, not the Production one).

In the Redirect URI field, paste exactly this:

```
http://localhost:8910/qbo-callback
```

No trailing slash. Case-sensitive. The port 8910 matches what the `qbo-authorize.sh` script will listen on locally.

Click Save.

### 4g. Reconnect URL (mandatory as of Feb 24, 2026)

Look for the **Reconnect URL** field, either on the same Redirect URIs page or a separate Reconnect URL section. Paste the same value:

```
http://localhost:8910/qbo-callback
```

Click Save.

## Step 5 — Run the OAuth authorization script

Once Step 4 is complete and the Development Redirect URI is saved, run:

```bash
bash /home/john/repos/Bookie/scripts/qbo-authorize.sh
```

A browser window opens to Intuit's authorize page. Sign in with the same `john@husband.llc` account. Choose your sandbox QBO company (Intuit auto-provisioned one when you created the developer account). Click Authorize. The browser shows "Authorized. You can close this tab."

The script captures the `refresh_token`, `realm_id`, and `refresh_token_expires_at`, and writes them into `/home/john/.config/bookie/qbo-credentials.json`. Verify with:

```bash
python3 -c "import json; d=json.load(open('/home/john/.config/bookie/qbo-credentials.json')); print('refresh_token ok:', bool(d['refresh_token'])); print('realm_id ok:', bool(d['realm_id']))"
```

Both should print `ok: True`.

## Step 6 — Create the Bookie bot Intuit user

This is a separate Intuit account that Bookie will use to drive the QBO web UI when browser automation kicks in. The QBO audit log will show this bot user as the actor for browser-driven actions, not you.

Decide on a bot email. Two easy options:

- **Gmail alias**: if your personal Gmail is `something@gmail.com`, use `something+bookie@gmail.com` — mail to that alias routes to your normal inbox. No Gmail config needed.
- **Your own domain**: `bookie@husband.llc` if you control mail delivery for the husband.llc domain.

Go to https://accounts.intuit.com/signup and create a new Intuit account with the bot email and a strong password. Save the password in your password manager.

Verify the email when Intuit sends a confirmation link.

## Step 7 — Invite the Bookie bot to your QBO company

Sign into https://qbo.intuit.com as yourself (`john@husband.llc`), in your Husband.LLC company.

Click the **gear icon** in the top right, then **Manage users** (or **Users**, depending on the QBO UI version).

Click **Add user**.

- **Role:** Standard user → All access (Company Admin if you want Bookie to also manage Bank Rules — recommended for the full experience).
- **Email:** the bot email from Step 6.

Click Send Invite.

Open the bot email's inbox, find Intuit's invitation, click Accept, and complete the bot account's first sign-in to QBO.

## Step 8 — Capture a logged-in browser session for the bot

This is the one-time MFA. The headless browser runs Bookie uses afterward will reuse this captured session and skip MFA going forward.

Run:

```bash
bash /home/john/repos/Bookie/scripts/capture-browser-session.sh
```

A real Chromium window opens to qbo.intuit.com. Sign in **as the Bookie bot user** (the email and password from Step 6, NOT your personal account).

Complete the MFA challenge — you'll get a verification code by SMS or email.

When prompted "Trust this device?", click **Yes**.

Verify you can see Husband.LLC's books as the bot (Bookie has access because of Step 7).

Return to the terminal that's still running the script.

Press **Enter** in the terminal. The script captures the session cookies into `/home/john/.config/bookie/qbo-storage-state.json` and closes the browser.

## Step 9 — Sanity check the laptop

Verify all credential files are in place:

```bash
ls -la /home/john/.config/bookie/
```

You should see at least:

- `qbo-credentials.json` (Steps 3 and 5 wrote to it)
- `qbo-storage-state.json` (Step 8 wrote to it)

Both should have `-rw-------` permissions.

Run Bookie's self-check to confirm the categorizer still works:

```bash
bash /home/john/repos/Bookie/bin/bookie self-check
```

You should see `self-check OK` at the end.

## Step 10 — Ship credentials to the VPS

The Hetzner VPS at `178.156.191.113` runs the OpenHarness daemon continuously. It needs the credential files to actually do real bookkeeping. Run:

```bash
bash /home/john/repos/OpenHarness/deploy/ship-credentials.sh
```

The script does the following:

- SCPs `qbo-credentials.json` and `qbo-storage-state.json` from `/home/john/.config/bookie/` to `/root/.config/bookie/` on the VPS with `0600` permissions.
- Restarts the `openharness-daemon.service` on the VPS.
- Waits 4 seconds and tails the journal for the last 10 seconds, checking for `traceback`, `FATAL`, `cannot load provider`, `json decode`, or `config missing` strings.
- Exits with code 0 (success) only if the daemon is active and the log is clean.

You should see output ending with `Daemon active, no errors in last 10s. Done.`

## Step 11 — Watch Bookie's first tick

Within 60 seconds of Step 10 completing, the VPS daemon ticks. Because the credentials are now present and Bookie has never inspected your books before, the first tick runs a **first-inspection**:

1. Pulls your Chart of Accounts from QBO (all the GL codes you have)
2. Pulls your vendor list
3. Pulls any RecurringTransaction templates (memorized transactions)
4. Writes a summary to `/opt/openharness-deploy/OpenHarness/inbox/bookie.md` on the VPS
5. Persists raw inspection data under `/opt/openharness-deploy/OpenHarness/employees/bookie/workspace/inspection/`
6. git-pushes the state change to GitHub

To watch this happen, on your laptop run:

```bash
cd /home/john/repos/OpenHarness
sleep 90
git pull --no-edit
tail -30 inbox/bookie.md
```

You should see a message like "First inspection of your QBO complete. Here's what I found: Chart of Accounts: 47 accounts. Vendors: 23 on file. Recurring transaction templates: 4." (The numbers depend on your actual QBO setup.)

That message confirms Bookie has read your books and is ready to start categorizing.

## After sandbox is working

The setup above puts Bookie in QBO **sandbox** mode. Bookie reads from and writes to Intuit's sandbox QBO tenant, not your real books. That's intentional for the first phase — same code, same logic, same architecture, but no risk to real data.

To move to **production** (Bookie operating on your real Husband.LLC QBO), three things are required:

1. **Intuit App Assessment Questionnaire.** From the Intuit dashboard, request production keys. Intuit reviews your answers (app purpose, your organization, what data you'll access, security practices). Usually fast.
2. **HTTPS Redirect URI from a real domain.** Production strictly rejects `http://localhost`. You need a real domain like `bookie.husband.llc` with TLS (Caddy + Let's Encrypt) pointed at the Hetzner VPS, with the OAuth callback served at `https://bookie.husband.llc/qbo-callback`.
3. **Real EULA URL, privacy policy URL, and support email** that Intuit can review (replacing the placeholders from Step 4b).

I'll add a production setup checklist as a separate file (`BOOKIE-PRODUCTION.md`) once sandbox is fully working and you say go.

## Troubleshooting

### Step 4 — "Redirect URIs section still locked after I saved all the other tabs"

If saving the Settings tabs didn't unlock Redirect URIs, check:

- Are all required fields filled in on each tab? Intuit highlights missing required fields with red asterisks or borders.
- Did you click Save on each tab? Some tabs autosave; some require explicit Save.
- Try reloading the page after saving each tab — Intuit's UI sometimes caches the gate message even after the gate has technically been satisfied.
- If still blocked: try generating a Production key (toggle to Production tab in Keys & Credentials, click Show credentials). Some users report this unlocks the Development Redirect URI section even though it's logically separate.

### Step 5 — `qbo-authorize.sh` says "redirect URI mismatch"

The Redirect URI registered in Intuit must match exactly what the script sends. Verify:

- The Intuit-registered URI is exactly `http://localhost:8910/qbo-callback` (case-sensitive, no trailing slash)
- The script's hardcoded URI matches. Check with: `grep REDIRECT_URI /home/john/repos/Bookie/scripts/qbo-authorize.sh`

### Step 5 — Browser opens but Intuit shows "invalid_client"

Your Client ID or Client Secret in `/home/john/.config/bookie/qbo-credentials.json` doesn't match what's registered. Verify the file contains the **Development** keys (not Production), copied without trailing whitespace:

```bash
python3 -c "import json; d=json.load(open('/home/john/.config/bookie/qbo-credentials.json')); print('client_id len:', len(d['client_id'])); print('client_secret len:', len(d['client_secret']))"
```

Typical Intuit Development Client ID is around 50 characters; Client Secret is around 40 characters. If the lengths are very different, the values were truncated or have stray whitespace.

### Step 8 — `capture-browser-session.sh` fails to install Playwright

The script tries to install Playwright via pip if not present. If your Python install blocks pip installs (PEP 668):

```bash
pip install --user --break-system-packages playwright
python3 -m playwright install chromium
```

Then re-run `bash /home/john/repos/Bookie/scripts/capture-browser-session.sh`.

### Step 10 — `ship-credentials.sh` fails with "permission denied" on SSH

Verify the SSH key:

```bash
ssh -i /home/john/.ssh/cto-deploy -o BatchMode=yes root@178.156.191.113 'echo ok'
```

Should print `ok`. If it asks for a password or fails, the key isn't right.

### Step 11 — first-inspection doesn't appear in inbox/bookie.md

Check the VPS daemon journal:

```bash
ssh -i /home/john/.ssh/cto-deploy root@178.156.191.113 "export XDG_RUNTIME_DIR=/run/user/0 && journalctl --user -u openharness-daemon.service --since '5 minutes ago' --no-pager" | tail -50
```

Look for tracebacks or "tick FAILED" lines. Most common causes: bad QBO credentials, QBO API rate limit, missing OAuth scope.

## Key file paths and commands (single reference)

- **QBO credentials on laptop:** `/home/john/.config/bookie/qbo-credentials.json`
- **Browser session storage on laptop:** `/home/john/.config/bookie/qbo-storage-state.json`
- **OAuth handshake script:** `/home/john/repos/Bookie/scripts/qbo-authorize.sh`
- **Browser session capture script:** `/home/john/repos/Bookie/scripts/capture-browser-session.sh`
- **Credential shipping script:** `/home/john/repos/OpenHarness/deploy/ship-credentials.sh`
- **Bookie self-check:** `/home/john/repos/Bookie/bin/bookie self-check`
- **Bookie inbox (after Step 10):** `/home/john/repos/OpenHarness/inbox/bookie.md`
- **VPS daemon journal:** `ssh -i /home/john/.ssh/cto-deploy root@178.156.191.113 "export XDG_RUNTIME_DIR=/run/user/0 && journalctl --user -u openharness-daemon.service -f"`
- **Hetzner VPS IP:** `178.156.191.113`
- **OpenHarness goal verify:** `cd /home/john/repos/OpenHarness && ./bin/harness goal verify`
