#!/usr/bin/env bash
# qbo-authorize.sh — interactive OAuth flow for QuickBooks Online sandbox.
#
# Prereqs:
#   1. You have an Intuit Developer account (developer.intuit.com)
#   2. You created an app there; copy its Client ID and Client Secret into
#      ~/.config/bookie/qbo-credentials.json (start from
#      config/qbo-credentials.template.json)
#   3. Your app has http://localhost:8910/qbo-callback as a Redirect URI
#
# This script:
#   - Spins up a tiny local HTTP server on :8910 to catch the OAuth redirect
#   - Opens your browser to Intuit's authorize URL
#   - You sign in and approve; Intuit redirects to the local server
#   - The server captures `code` and `realmId`, exchanges them for tokens
#   - Writes refresh_token + realm_id back into ~/.config/bookie/qbo-credentials.json

set -euo pipefail

CONFIG="${BOOKIE_CONFIG_ROOT:-$HOME/.config/bookie}/qbo-credentials.json"
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: $CONFIG not found. Copy from config/qbo-credentials.template.json first." >&2
  exit 1
fi

python3 - "$CONFIG" <<'PY'
import json, sys, webbrowser, http.server, urllib.parse, urllib.request, base64

CONFIG = sys.argv[1]
with open(CONFIG) as f:
    cfg = json.load(f)
if not cfg.get("client_id") or not cfg.get("client_secret"):
    print(f"ERROR: client_id and client_secret must be populated in {CONFIG}", file=sys.stderr)
    sys.exit(1)

CLIENT_ID = cfg["client_id"]
CLIENT_SECRET = cfg["client_secret"]
ENV = cfg.get("environment", "sandbox")
REDIRECT_URI = "http://localhost:8910/qbo-callback"
SCOPE = "com.intuit.quickbooks.accounting"
STATE = base64.urlsafe_b64encode(b"bookie-oauth").decode()

authorize_url = (
    "https://appcenter.intuit.com/connect/oauth2"
    f"?client_id={urllib.parse.quote(CLIENT_ID)}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={urllib.parse.quote(SCOPE)}"
    f"&response_type=code"
    f"&state={STATE}"
)

print("Opening browser to authorize...")
print(f"If it doesn't open: {authorize_url}")
webbrowser.open(authorize_url)

result = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass
    def do_GET(self):
        if "/qbo-callback" not in self.path:
            self.send_response(404); self.end_headers(); return
        qs = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(qs))
        result["code"] = params.get("code", "")
        result["realmId"] = params.get("realmId", "")
        result["state"] = params.get("state", "")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Authorized. You can close this tab.</h1>")

server = http.server.HTTPServer(("127.0.0.1", 8910), Handler)
print("Waiting for redirect on http://localhost:8910/qbo-callback ...")
while "code" not in result:
    server.handle_request()

print(f"Got authorization code (realmId={result['realmId']}). Exchanging for tokens...")
creds = f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
auth_header = base64.b64encode(creds).decode()
body = urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "code": result["code"],
    "redirect_uri": REDIRECT_URI,
}).encode()
req = urllib.request.Request(
    "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
    data=body,
    headers={"Authorization": f"Basic {auth_header}",
             "Content-Type": "application/x-www-form-urlencoded",
             "Accept": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as r:
    tok = json.loads(r.read().decode())

cfg["refresh_token"] = tok["refresh_token"]
cfg["access_token"] = tok["access_token"]
import time as _t
cfg["access_token_expires_at"] = _t.time() + int(tok.get("expires_in", 3600)) - 60
cfg["realm_id"] = result["realmId"]
with open(CONFIG, "w") as f:
    json.dump(cfg, f, indent=2)
import os
os.chmod(CONFIG, 0o600)
print(f"OK — wrote refresh_token and realm_id to {CONFIG}")
print(f"   Environment: {ENV}")
print(f"   Realm: {result['realmId']}")
PY

echo
echo "Verify with: python3 -c \"from bookie.qbo import load_config, fetch_chart_of_accounts; cfg = load_config('$CONFIG'); print(len(fetch_chart_of_accounts(cfg, '$CONFIG')), 'accounts in CoA')\""
