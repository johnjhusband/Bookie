#!/usr/bin/env bash
# install.sh — reproducible Bookie setup.
# A single command from a fresh clone produces a working install.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "==> Verifying Python 3.10+..."
python3 -c "import sys; assert sys.version_info >= (3, 10), 'need Python 3.10+'"

echo "==> Making bin/bookie executable..."
chmod +x bin/bookie

echo "==> Ensuring config dir exists..."
CONFIG_DIR="${BOOKIE_CONFIG_ROOT:-$HOME/.config/bookie}"
mkdir -p "$CONFIG_DIR"
target="$CONFIG_DIR/qbo-credentials.json"
if [ ! -f "$target" ]; then
  cp "config/qbo-credentials.template.json" "$target"
  chmod 600 "$target"
  echo "    Seeded $target from template — fill in your QuickBooks Online credentials before going live."
else
  echo "    $target already exists; leaving it untouched."
fi

echo "==> Running tests..."
python3 -m pytest -q tests/

echo
echo "==> Bookie installed."
echo "    Add to PATH:  export PATH=\"$HERE/bin:\$PATH\""
echo "    Then run:     bookie company    # proves you're on the live books"
echo
echo "    Brain: Bookie reasons via the 'claude' CLI on your own subscription (no API key)."
echo "    Tell Bookie about your business: set BOOKIE_BUSINESS_PROFILE to a private file"
echo "    describing it (see README → 'Tell Bookie about your business')."
