#!/usr/bin/env bash
# ==============================================================================
# Wireless Analyzer Platform - Kali Linux / Debian / Ubuntu Installer
# Idempotent, least-privilege installation and environment repair script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure src is ALWAYS in PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

FORCE_REBUILD=0

# Parse CLI options
for arg in "$@"; do
    case "$arg" in
        --fix|--repair|--force|--clean|--reinstall)
            FORCE_REBUILD=1
            ;;
        --help|-h)
            echo "Wireless Analyzer Installation & Setup Script"
            echo ""
            echo "Usage: ./install.sh [options]"
            echo ""
            echo "Options:"
            echo "  --fix, --repair, --clean, --force   Force recreate virtual environment from scratch"
            echo "  --help, -h                          Show this help message"
            exit 0
            ;;
    esac
done

echo "======================================================================"
echo "          WIRELESS ANALYZER — INSTALLATION & ENVIRONMENT SETUP        "
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. Detect Python 3.11+
# ------------------------------------------------------------------------------
echo "[*] Step 1: Checking Python runtime..."
PYTHON_BIN=""

for candidate in python3 python python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VERSION=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        if [ -n "$MAJOR" ] && [ -n "$MINOR" ] && [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_BIN=$(command -v "$candidate")
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] ERROR: Python 3.11 or higher is required."
    echo "    On Kali/Debian/Ubuntu, install it with:"
    echo "    sudo apt update && sudo apt install -y python3 python3-venv python3-pip python3-full"
    exit 1
fi

echo "    [✓] Found compatible Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# ------------------------------------------------------------------------------
# 2. Virtual Environment Setup & Validation
# ------------------------------------------------------------------------------
echo "[*] Step 2: Configuring Python virtual environment (.venv)..."

if [ "$FORCE_REBUILD" -eq 1 ] && [ -d ".venv" ]; then
    echo "    [*] Forced rebuild requested: Removing old .venv..."
    rm -rf .venv
fi

# Check if existing .venv is healthy
if [ -d ".venv" ]; then
    TEST_PY="$SCRIPT_DIR/.venv/bin/python"
    [ ! -f "$TEST_PY" ] && [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ] && TEST_PY="$SCRIPT_DIR/.venv/Scripts/python.exe"
    
    # Test if existing venv python works
    if [ ! -f "$TEST_PY" ] || ! "$TEST_PY" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
        echo "    [!] Existing .venv is broken (e.g. system Python was upgraded). Recreating..."
        rm -rf .venv
    else
        echo "    Reusing existing healthy virtual environment (.venv)..."
    fi
fi

if [ ! -d ".venv" ]; then
    echo "    Creating new virtual environment at .venv..."
    if ! "$PYTHON_BIN" -m venv .venv 2>/dev/null; then
        echo "    [*] Standard venv creation failed or warned. Trying fallback mode..."
        "$PYTHON_BIN" -m venv --without-pip .venv || {
            echo "[!] ERROR: Failed to create virtual environment."
            echo "    On Kali/Debian/Ubuntu, please install python3-venv:"
            echo "    sudo apt update && sudo apt install -y python3-venv python3-pip python3-full"
            exit 1
        }
    fi
fi

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ] && [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
fi

# ------------------------------------------------------------------------------
# 3. Bootstrap Pip inside .venv if missing
# ------------------------------------------------------------------------------
echo "[*] Step 3: Verifying pip inside virtual environment..."
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "    [*] Bootstrapping pip via ensurepip..."
    "$VENV_PYTHON" -m ensurepip --upgrade 2>/dev/null || "$VENV_PYTHON" -m ensurepip --default-pip 2>/dev/null || true
fi

# Fallback to get-pip.py if ensurepip is stripped on Debian/Kali
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "    [*] Ensurepip unavailable, downloading get-pip.py bootstrap..."
    if command -v curl >/dev/null 2>&1; then
        curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_PYTHON" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://bootstrap.pypa.io/get-pip.py | "$VENV_PYTHON" || true
    fi
fi

if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "[!] ERROR: Could not bootstrap pip inside the virtual environment."
    echo "    Please run:"
    echo "    sudo apt update && sudo apt install -y python3-venv python3-pip python3-full"
    exit 1
fi
echo "    [✓] Pip ready: $("$VENV_PYTHON" -m pip --version)"

# ------------------------------------------------------------------------------
# 4. Install Dependencies
# ------------------------------------------------------------------------------
echo "[*] Step 4: Installing Python package dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
"$VENV_PYTHON" -m pip install -r requirements.txt
"$VENV_PYTHON" -m pip install -e . --no-deps >/dev/null 2>&1 || true

# ------------------------------------------------------------------------------
# 5. Create Project Directories
# ------------------------------------------------------------------------------
echo "[*] Step 5: Ensuring runtime directories exist..."
mkdir -p data/oui config exports

# ------------------------------------------------------------------------------
# 6. Check System Wireless & Bluetooth Tooling
# ------------------------------------------------------------------------------
echo "[*] Step 6: Auditing Linux wireless utilities..."
for tool in nmcli iw bluetoothctl sqlite3 rfkill; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "    [✓] $tool : $(command -v "$tool")"
    else
        echo "    [○] $tool : Not found in PATH (Optional, fallback backends will engage)"
    fi
done

# ------------------------------------------------------------------------------
# 7. Run Pre-flight Diagnostics Verification
# ------------------------------------------------------------------------------
echo "[*] Step 7: Verifying installation via diagnostics..."
"$VENV_PYTHON" -m application diag

echo ""
echo "======================================================================"
echo "[✓] Installation completed successfully!"
echo "    Start the application with:"
echo "    ./run.sh"
echo "    or (mock demo mode):"
echo "    ./run.sh --mock"
echo "    or repair anytime with:"
echo "    ./run.sh --fix"
echo "======================================================================"
