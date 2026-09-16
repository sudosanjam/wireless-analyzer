#!/usr/bin/env bash
# ==============================================================================
# Signal Observer Platform - Kali Linux / Debian / Ubuntu Installer
# Idempotent, least-privilege installation script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "          SIGNAL OBSERVER — INSTALLATION & ENVIRONMENT SETUP          "
echo "======================================================================"

# 1. Detect Python 3.11+
echo "[*] Step 1: Checking Python runtime..."
PYTHON_BIN=""

for candidate in python3 python python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VERSION=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_BIN=$(command -v "$candidate")
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] ERROR: Python 3.11 or higher is required."
    echo "    On Kali/Debian/Ubuntu, install it with:"
    echo "    sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

echo "    [✓] Found compatible Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# 2. Virtual Environment Setup
echo "[*] Step 2: Configuring Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    echo "    Creating new virtual environment at .venv..."
    "$PYTHON_BIN" -m venv .venv
else
    echo "    Reusing existing virtual environment (.venv)..."
fi

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"

# Ensure venv executables exist (handle Windows/POSIX venv paths if on bash-on-windows)
if [ ! -f "$VENV_PYTHON" ] && [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
    VENV_PIP="$SCRIPT_DIR/.venv/Scripts/pip.exe"
fi

# 3. Upgrade Pip & Install Dependencies
echo "[*] Step 3: Installing Python package dependencies..."
"$VENV_PIP" install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
"$VENV_PIP" install -r requirements.txt
"$VENV_PIP" install -e . --no-deps >/dev/null 2>&1 || true

# 4. Create Project Directories
echo "[*] Step 4: Ensuring runtime directories exist..."
mkdir -p data/oui config exports

# 5. Check System Wireless & Bluetooth Tooling
echo "[*] Step 5: Auditing Linux wireless utilities..."
for tool in nmcli iw bluetoothctl sqlite3; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "    [✓] $tool : $(command -v "$tool")"
    else
        echo "    [○] $tool : Not found in PATH (Optional, fallback backends will engage)"
    fi
done

# 6. Run Pre-flight Diagnostics Verification
echo "[*] Step 6: Verifying installation via diagnostics..."
"$VENV_PYTHON" -m application diag

echo ""
echo "======================================================================"
echo "[✓] Installation completed successfully!"
echo "    Start the application with:"
echo "    ./run.sh"
echo "    or (mock demo mode):"
echo "    ./run.sh --mock"
echo "======================================================================"
