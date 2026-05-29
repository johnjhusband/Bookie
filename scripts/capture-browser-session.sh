#!/usr/bin/env bash
# capture-browser-session.sh — capture a logged-in QBO browser session for headless reuse.
#
# Run this ONCE after you've created the dedicated Bookie Intuit user and
# invited it to Husband.LLC's QBO. It opens a real Chromium window, lets you
# log in as Bookie + complete MFA + click "Trust this device", then saves the
# session storageState to ~/.config/bookie/qbo-storage-state.json.
#
# Headless Bookie runs will reuse that storage state and skip MFA going forward.

set -euo pipefail

STORAGE="${BOOKIE_BROWSER_STORAGE_STATE:-$HOME/.config/bookie/qbo-storage-state.json}"
mkdir -p "$(dirname "$STORAGE")"

if ! python3 -c "import playwright" 2>/dev/null; then
  echo "Installing playwright..."
  pip install --user --break-system-packages playwright
  python3 -m playwright install chromium
fi

python3 - "$STORAGE" <<'PY'
import sys, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

STORAGE = sys.argv[1]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    print("==> Opening QBO. Sign in as your Bookie bot user, complete MFA,")
    print("    and confirm 'Trust this device' if asked.")
    print("    Verify you can see Husband.LLC's books, then return here.")
    page.goto("https://qbo.intuit.com")

    input("\n==> Press Enter HERE in the terminal once you're fully signed in and inside QBO... ")

    state = context.storage_state()
    Path(STORAGE).write_text(json.dumps(state, indent=2))
    Path(STORAGE).chmod(0o600)
    print(f"==> Saved storage state to {STORAGE}")
    print(f"    {len(state.get('cookies', []))} cookies captured.")
    browser.close()
PY

echo
echo "==> Done. Headless Bookie runs will now reuse this session and skip MFA."
echo "    To verify the session works, run:"
echo "      python3 -c \"from bookie.browser import is_available; print('OK' if is_available() else 'FAIL')\""
