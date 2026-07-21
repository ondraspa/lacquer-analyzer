#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/venv"
cd "$ROOT"

echo "=== lacquer_analyzer — setup ==="
echo ""

# ── 1. System dependencies (optional, user-skippable) ──────────
if command -v sudo &>/dev/null; then
    echo "System packages needed: tesseract-ocr, tesseract-lang, unrar"
    echo "Install now? [y/N] "
    read -r ans
    if [[ "$ans" =~ ^[yY] ]]; then
        UNAME="$(uname -s)"
        if [[ "$UNAME" == "Linux" ]]; then
            . /etc/os-release 2>/dev/null || true
            if [[ -n "${ID_LIKE:-}" && "$ID_LIKE" == *"arch"* ]] || [[ "${ID:-}" == "arch" || "${ID:-}" == "manjaro" ]]; then
                sudo pacman -S --noconfirm --needed tesseract tesseract-data-eng tesseract-data-ces unrar
            elif command -v apt-get &>/dev/null; then
                sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ces unrar
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y tesseract tesseract-langpack-eng tesseract-langpack-ces unrar
            else
                echo "⚠  Unknown distro — install manually: tesseract + unrar"
            fi
        elif [[ "$UNAME" == "Darwin" ]] && command -v brew &>/dev/null; then
            brew install tesseract unrar
            brew install tesseract-lang || true
        fi
    else
        echo "Skipping system packages."
    fi
fi

# ── 2. Python venv ─────────────────────────────────────────────
if [[ ! -d "$VENV" ]]; then
    echo "Creating virtual environment…"
    python3 -m venv "$VENV"
fi

echo "Installing Python packages…"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$ROOT/requirements.txt"

# ── 3. Playwright browser ──────────────────────────────────────
echo "Installing Playwright Chromium browser…"
# --with-deps may fail on unsupported distros (Arch); that's OK
"$VENV/bin/python" -m playwright install chromium 2>&1 | tail -3
"$VENV/bin/python" -m playwright install-deps chromium 2>/dev/null || true

# ── 4. Done ────────────────────────────────────────────────────
echo ""
echo "=== Done ==="
echo ""
echo "Launch:  ./venv/bin/python main.py"
echo "Re-run setup any time to update dependencies."
