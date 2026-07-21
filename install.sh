#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== lacquer_analyzer — dependency installer ==="
echo ""

# ── Detect OS ──────────────────────────────────────────────────────
UNAME="$(uname -s)"
PKG_MGR=""
INSTALL_CMD=""
TESSERACT_PKG=""
TESSDATA_PREFIX=""

if [[ -f /etc/os-release ]]; then
    . /etc/os-release
fi

install_system_packages() {
    echo "  Installing system packages via $PKG_MGR..."
    echo "    Packages: $*"
    sudo $INSTALL_CMD "$@"
    echo ""
}

if [[ "$UNAME" == "Linux" ]]; then
    if [[ -n "${ID_LIKE:-}" && "$ID_LIKE" == *"arch"* ]] || [[ "${ID:-}" == "arch" || "${ID:-}" == "garuda" || "${ID:-}" == "manjaro" ]]; then
        PKG_MGR="pacman"
        INSTALL_CMD="pacman -S --noconfirm --needed"
        install_system_packages \
            tesseract tesseract-data-eng tesseract-data-ces \
            unrar
    elif command -v apt-get &>/dev/null; then
        PKG_MGR="apt-get"
        INSTALL_CMD="apt-get install -y"
        install_system_packages \
            tesseract-ocr tesseract-ocr-eng tesseract-ocr-ces \
            unrar
    elif command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
        INSTALL_CMD="dnf install -y"
        install_system_packages \
            tesseract tesseract-langpack-eng tesseract-langpack-ces \
            unrar
    elif command -v zypper &>/dev/null; then
        PKG_MGR="zypper"
        INSTALL_CMD="zypper install -y"
        install_system_packages \
            tesseract-ocr tesseract-ocr-traineddata-english \
            tesseract-ocr-traineddata-czech unrar
    else
        echo "  ⚠  Linux distro not recognized ($PRETTY_NAME)."
        echo "     Please install manually:"
        echo "       - tesseract-ocr (OCR engine)"
        echo "       - tesseract-ocr-eng (English language data)"
        echo "       - tesseract-ocr-ces (Czech language data)"
        echo "       - unrar (RAR support)"
        echo ""
    fi

elif [[ "$UNAME" == "Darwin" ]]; then
    if command -v brew &>/dev/null; then
        echo "  Installing system packages via Homebrew..."
        brew install tesseract unrar
        # Install some language data
        brew install tesseract-lang || true
        echo ""
    else
        echo "  ⚠  Homebrew not found. Install it from https://brew.sh"
        echo ""
    fi
else
    echo "  ⚠  Unsupported OS: $UNAME"
    echo "     Install Tesseract manually, then run pip install."
    echo ""
fi

# ── Python packages ────────────────────────────────────────────────
if command -v pip3 &>/dev/null; then
    PIP="pip3"
elif command -v pip &>/dev/null; then
    PIP="pip"
else
    echo "ERROR: pip not found. Install Python 3 + pip first."
    exit 1
fi

echo "=== Installing Python packages ==="
"$PIP" install --upgrade pip
"$PIP" install -r "$ROOT/requirements.txt"
echo ""

# ── Playwright Chromium browser ────────────────────────────
echo "=== Installing Playwright Chromium browser ==="
if python3 -c "import playwright" 2>/dev/null; then
    python3 -m playwright install chromium 2>&1 | tail -3
    echo ""
else
    echo "  ⚠ playwright Python package not found — skipping browser install"
    echo "    (it should have been installed via requirements.txt above)"
    echo ""
fi

# ── Verification ───────────────────────────────────────────────────
echo "=== Verifying installation ==="
python3 -c "
from src.pdf_import import check_dependencies
ok, msg = check_dependencies()
print(msg)
" 2>/dev/null && echo "" || {
    echo "(run 'python3 main.py' from $ROOT to test the GUI)"
    echo ""
}

echo "=== Done ==="
echo "Run:  cd $ROOT && python3 main.py"
