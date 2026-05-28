#!/usr/bin/env bash
# plaid-link.sh — interactive Plaid Link OAuth flow.
#
# Prereqs:
#   1. You have a Plaid account (dashboard.plaid.com)
#   2. You copied your client_id + secret into ~/.config/bookie/plaid-credentials.json
#      (start from config/plaid-credentials.template.json)
#
# This script:
#   - Creates a link_token via Plaid API
#   - Opens a tiny local page that loads Plaid Link with that token
#   - You select your bank and complete the OAuth flow with the bank
#   - The page receives a public_token; the local server exchanges it for an access_token
#   - Writes the access_token into ~/.config/bookie/plaid-items.json

set -euo pipefail

CONFIG="${BOOKIE_CONFIG_ROOT:-$HOME/.config/bookie}/plaid-credentials.json"
ITEMS="${BOOKIE_CONFIG_ROOT:-$HOME/.config/bookie}/plaid-items.json"
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: $CONFIG not found. Copy from config/plaid-credentials.template.json first." >&2
  exit 1
fi
[ ! -f "$ITEMS" ] && echo '{"items":[]}' > "$ITEMS" && chmod 600 "$ITEMS"

python3 - "$CONFIG" "$ITEMS" <<'PY'
import json, sys, webbrowser, http.server, urllib.parse, urllib.request

CONFIG_PATH = sys.argv[1]
ITEMS_PATH = sys.argv[2]
with open(CONFIG_PATH) as f:
    cfg = json.load(f)
if not cfg.get("client_id") or not cfg.get("secret"):
    print(f"ERROR: client_id and secret must be populated in {CONFIG_PATH}", file=sys.stderr)
    sys.exit(1)

HOST = {"sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com"}[cfg.get("environment", "sandbox")]

# 1. Create a link_token
req = urllib.request.Request(
    f"{HOST}/link/token/create",
    data=json.dumps({
        "client_id": cfg["client_id"],
        "secret": cfg["secret"],
        "user": {"client_user_id": "bookie"},
        "client_name": "Bookie",
        "products": ["transactions"],
        "country_codes": ["US"],
        "language": "en",
    }).encode(),
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as r:
    link_token = json.loads(r.read().decode())["link_token"]
print(f"link_token: {link_token[:20]}...")

# 2. Tiny HTML page that runs Plaid Link
HTML = f"""<!doctype html><html><head><title>Bookie — Plaid Link</title></head>
<body style="font-family:system-ui;padding:2em;max-width:40em">
<h2>Connect your bank to Bookie</h2>
<p>Click below to open Plaid Link. Choose your institution and sign in.</p>
<button id="link" style="font-size:1.2em;padding:0.6em 1.2em;cursor:pointer">Connect bank</button>
<p id="status" style="margin-top:2em;color:#555"></p>
<script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
<script>
const handler = Plaid.create({{
  token: '{link_token}',
  onSuccess: (public_token, metadata) => {{
    fetch('/exchange', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{public_token, institution_name: metadata.institution.name}}),
    }}).then(r => r.text()).then(t => {{
      document.getElementById('status').innerText = 'Connected: ' + metadata.institution.name + ' — you can close this tab.';
    }});
  }},
  onExit: (err, metadata) => {{
    document.getElementById('status').innerText = err ? 'Exited with error: ' + err.error_message : 'Exited.';
  }},
}});
document.getElementById('link').onclick = () => handler.open();
</script>
</body></html>"""

results = []

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(HTML.encode())
    def do_POST(self):
        if self.path != "/exchange":
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n).decode())
        public_token = payload["public_token"]
        institution = payload.get("institution_name", "Unknown Bank")
        # exchange
        req = urllib.request.Request(
            f"{HOST}/item/public_token/exchange",
            data=json.dumps({"client_id": cfg["client_id"], "secret": cfg["secret"],
                             "public_token": public_token}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            access = json.loads(r.read().decode())["access_token"]
        results.append({"institution_name": institution, "access_token": access, "cursor": ""})
        self.send_response(200)
        self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(b"ok")

server = http.server.HTTPServer(("127.0.0.1", 8911), Handler)
print("Server on http://localhost:8911")
webbrowser.open("http://localhost:8911")
print("Waiting for bank connection...")
while not results:
    server.handle_request()

with open(ITEMS_PATH) as f:
    items_doc = json.load(f)
items_doc.setdefault("items", []).extend(results)
with open(ITEMS_PATH, "w") as f:
    json.dump(items_doc, f, indent=2)
import os; os.chmod(ITEMS_PATH, 0o600)
for r in results:
    print(f"Connected: {r['institution_name']} → access_token stored.")
print(f"All items in {ITEMS_PATH}")
PY
