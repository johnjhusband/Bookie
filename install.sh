#!/usr/bin/env bash
# install.sh — reproducible Bookie setup
# Per [install-must-be-reproducible-from-repo]: single command produces a working install.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "==> Verifying Python 3.10+..."
python3 -c "import sys; assert sys.version_info >= (3, 10), 'need Python 3.10+'"

echo "==> Making bin/bookie executable..."
chmod +x bin/bookie

echo "==> Running self-check (categorizer on a synthetic transaction set)..."
./bin/bookie self-check

OPENHARNESS_ROOT="${OPENHARNESS_ROOT:-/home/john/repos/OpenHarness}"
if [ -d "$OPENHARNESS_ROOT" ]; then
  EMP_DIR="$OPENHARNESS_ROOT/employees/bookie"
  if [ -d "$EMP_DIR" ]; then
    echo "==> Syncing employee-workspace/ → $EMP_DIR (canonical source)..."
    for f in employee-workspace/*.md; do
      cp "$f" "$EMP_DIR/$(basename "$f")"
    done
    echo "    Synced. To re-sync after edits in this repo: re-run install.sh."
  else
    echo "==> OpenHarness present but bookie not installed; run: harness employee install bookie"
  fi
else
  echo "==> OpenHarness not found at $OPENHARNESS_ROOT; skipping workspace sync."
fi

echo
echo "==> Bookie installed."
echo "    Add to PATH:  export PATH=\"$HERE/bin:\$PATH\""
echo "    First run:    bookie self-check"
