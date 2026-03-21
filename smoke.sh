#!/usr/bin/env bash
set -euo pipefail

# One-command release smoke test for lore.
# - Creates an isolated temp workspace + venv
# - Installs the current project as a normal package
# - Runs core CLI checks
#
# Usage:
#   ./smoke.sh
# Optional env vars:
#   PYTHON_BIN=python3.12   # choose interpreter
#   KEEP_SMOKE=1            # keep temp workspace for debugging

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
KEEP_SMOKE="${KEEP_SMOKE:-0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[smoke] error: interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi

SMOKE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/lore-smoke.XXXXXX")"
VENV_DIR="$SMOKE_ROOT/.venv"
TEST_REPO="$SMOKE_ROOT/project"

cleanup() {
  if [[ "$KEEP_SMOKE" == "1" ]]; then
    echo "[smoke] keeping workspace: $SMOKE_ROOT"
    return
  fi
  rm -rf "$SMOKE_ROOT"
}
trap cleanup EXIT

echo "[smoke] workspace: $SMOKE_ROOT"
echo "[smoke] python: $PYTHON_BIN"

"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

python -m pip install -U pip setuptools wheel
python -m pip install "$ROOT_DIR"

echo "[smoke] step: lore version"
lore version

mkdir -p "$TEST_REPO"
cd "$TEST_REPO"

echo "[smoke] step: lore init"
lore init .

echo "[smoke] step: lore add"
lore add facts "smoke test memory"

echo "[smoke] step: trust refresh (dry run)"
lore trust refresh --dry-run

echo "[smoke] step: export chronicle"
lore export --format chronicle

test -f "$TEST_REPO/CHRONICLE.md"

echo "[smoke] success: CLI smoke test passed"
