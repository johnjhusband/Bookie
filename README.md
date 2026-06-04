# Bookie

An AI bookkeeper for QuickBooks Online. **Claude is the brain; the code is only plumbing.**

Bookie connects to your QuickBooks Online company, reads your chart of accounts and the
transactions sitting in uncategorized buckets, and asks Claude to propose where each one
belongs — with a confidence score and a one-line rationale. It is **read-only until you
explicitly approve a change**.

There is no hardcoded categorization logic in this repo, and that is the point: the judgment
is the LLM's, reasoning about what each transaction actually is for *your* business — not a
keyword script.

## What you need

- **Python 3.10+**
- The **`claude` CLI** ([Claude Code](https://claude.com/claude-code)) installed and signed in.
  Bookie runs Claude on your own subscription — there is **no API key** to manage.
- A **QuickBooks Online** company and an **Intuit Developer** app (free) for OAuth credentials.

## Install

```bash
bash install.sh
export PATH="$PWD/bin:$PATH"
```

`install.sh` checks your Python, seeds a credentials file from the template, and runs the
unit tests.

## Connect to QuickBooks Online

1. At [developer.intuit.com](https://developer.intuit.com), create an app. Copy its
   **client_id** and **client_secret** (Development keys for sandbox; Production keys once
   your app is approved).
2. Run the OAuth 2.0 authorization-code flow once to get a **refresh_token** and your
   company's **realm_id**. (Intuit's OAuth Playground works, or any standard OAuth flow
   pointed at your app's redirect URI.)
3. Put those into `~/.config/bookie/qbo-credentials.json` (the install seeded a template
   there). Set `environment` to `sandbox` or `production`.

This file holds secrets and is **never** committed — it lives in your home directory, outside
the repo.

```bash
bookie company        # prints the connected company — proves you're on the real books
```

## Tell Bookie about your business

The more Bookie knows about what your business *does*, the better its categorization. Put a
plain-text description of your business in a private file (NOT in this repo) and point an
environment variable at it:

```bash
export BOOKIE_BUSINESS_PROFILE="$HOME/my-business-profile.txt"
```

That file might say, for example, *"a two-owner real-estate investment and private-lending
LLC: several rental properties in multiple states, loans to individuals, some equity
investments; cash basis."* Claude uses it to reason (e.g. a wire to a title company is a
property sale, not a bank fee). If the variable is unset, Bookie falls back to a generic
"a small business" and still works.

Keep anything private — owner names, account numbers, addresses, the realm ID — in that file
and in `~/.config/bookie/`, never in this repo.

## Commands

```bash
bookie company         # the connected company profile (live)
bookie coa             # the chart of accounts (live)
bookie uncategorized   # count transactions in uncategorized buckets (live)
bookie review          # Claude proposes a category for each uncategorized txn — READ-ONLY
bookie review --out proposals.json   # also write the proposals to a file (still posts nothing)
```

Nothing in these commands writes to your books. Writing back (e.g. reclassifying a
transaction) is a separate, deliberate step you approve.

## How it works

```
QuickBooks Online  ──(read)──►  bookie.qbo (REST v3 + OAuth)  ──►  bookie.brain (the claude CLI)
                                                                         │
                              proposals (account + confidence + why) ◄───┘
```

- `src/bookie/qbo.py` — QuickBooks Online client: OAuth refresh, chart of accounts, reports,
  reading uncategorized transactions, and a careful sparse-update for reclassifying one line.
- `src/bookie/brain.py` — builds the prompt, runs the `claude` CLI, parses its JSON answer.
  Carries no business-specific facts; the business description comes from
  `$BOOKIE_BUSINESS_PROFILE`.
- `src/bookie/cli.py` — the `bookie` commands above.
- `tests/` — unit tests for the brain (Claude call injected) and the QBO body-builders.

```bash
python3 -m pytest -q tests/
```

## Safety

- Read-only by default. A write only happens when you ask for it.
- Secrets live in `~/.config/bookie/qbo-credentials.json` and your private business profile —
  never in this repo. `.gitignore` blocks `*.local.md` and credential files.
- Every QBO write uses a `Request-Id` (idempotency) and `SyncToken` (optimistic concurrency).

## License

MIT.
