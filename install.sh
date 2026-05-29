#!/usr/bin/env bash
# install.sh — reproducible Bookie setup
# Per [install-must-be-reproducible-from-repo]: single command produces a working install.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "==> Verifying Python 3.10+..."
python3 -c "import sys; assert sys.version_info >= (3, 10), 'need Python 3.10+'"

echo "==> Making bin/bookie and scripts executable..."
chmod +x bin/bookie scripts/*.sh

echo "==> Ensuring ~/.config/bookie/ exists..."
mkdir -p "${BOOKIE_CONFIG_ROOT:-$HOME/.config/bookie}"
for f in qbo-credentials; do
  target="${BOOKIE_CONFIG_ROOT:-$HOME/.config/bookie}/${f}.json"
  if [ ! -f "$target" ]; then
    cp "config/${f}.template.json" "$target"
    chmod 600 "$target"
    echo "    Seeded $target from template (fill in credentials before going live)"
  fi
done

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
    # Sync skills/ subdirectory if present
    if [ -d employee-workspace/skills ]; then
      rm -rf "$EMP_DIR/skills"
      cp -r employee-workspace/skills "$EMP_DIR/skills"
      echo "    Skills synced: $(ls employee-workspace/skills | wc -l) skill(s)"
    fi
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
