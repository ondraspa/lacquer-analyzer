#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/venv"

if [[ ! -f "$VENV/bin/python" ]]; then
    echo "First launch — setting up virtual environment…"
    python3 -m venv "$VENV"
fi

# Ensure all deps are installed (fast skip if already satisfied)
"$VENV/bin/pip" install --quiet -r "$ROOT/requirements.txt" 2>/dev/null || {
    echo "Installing dependencies…"
    "$VENV/bin/pip" install -r "$ROOT/requirements.txt"
}

exec "$VENV/bin/python" "$ROOT/main.py"
