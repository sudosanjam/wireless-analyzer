#!/usr/bin/env bash
# ==============================================================================
# Wireless Analyzer Platform - Runner & Self-Healing Launcher
# Automatically resolves Python environment, exports PYTHONPATH, and launches app
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure src is ALWAYS in PYTHONPATH (prevents "No module named application" regardless of editable install state)
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

# ------------------------------------------------------------------------------
# Self-Healing & Environment Repair Function
# ------------------------------------------------------------------------------
repair_environment() {
    echo "======================================================================"
    echo "          WIRELESS ANALYZER — ENVIRONMENT REPAIR & SELF-HEALING        "
    echo "======================================================================"

    # 1. Locate compatible system Python (>= 3.11)
    echo "[*] Step 1: Locating host Python 3.11+ runtime..."
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
        echo "    On Kali Linux / Debian / Ubuntu, install with:"
        echo "    sudo apt update && sudo apt install -y python3 python3-venv python3-pip python3-full"
        return 1
    fi
    echo "    [✓] Found host Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

    # 2. Rebuild clean virtual environment
    echo "[*] Step 2: Rebuilding clean virtual environment (.venv)..."
    rm -rf "$SCRIPT_DIR/.venv"
    
    # Try standard venv creation
    if ! "$PYTHON_BIN" -m venv "$SCRIPT_DIR/.venv" 2>/dev/null; then
        echo "    [*] Standard venv creation returned warning/error, attempting --without-pip fallback..."
        "$PYTHON_BIN" -m venv --without-pip "$SCRIPT_DIR/.venv" || {
            echo "[!] ERROR: Failed to create virtual environment."
            echo "    Please install required Debian/Kali packages:"
            echo "    sudo apt update && sudo apt install -y python3-venv python3-pip python3-full"
            return 1
        }
    fi

    # Resolve venv python
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
    if [ ! -f "$VENV_PYTHON" ] && [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
        VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
    fi

    if [ ! -f "$VENV_PYTHON" ]; then
        echo "[!] ERROR: Virtualenv python binary missing after creation."
        return 1
    fi

    # 3. Ensure pip is installed & functional inside .venv
    echo "[*] Step 3: Bootstrapping and verifying pip inside .venv..."
    if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
        echo "    [*] Bootstrapping pip via ensurepip..."
        "$VENV_PYTHON" -m ensurepip --upgrade 2>/dev/null || "$VENV_PYTHON" -m ensurepip --default-pip 2>/dev/null || true
    fi

    # Fallback to get-pip.py if ensurepip was disabled by distro
    if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
        echo "    [*] Ensurepip unavailable, downloading get-pip.py bootstrap..."
        if command -v curl >/dev/null 2>&1; then
            curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_PYTHON" || true
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- https://bootstrap.pypa.io/get-pip.py | "$VENV_PYTHON" || true
        fi
    fi

    if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
        echo "[!] ERROR: Could not bootstrap pip in virtual environment."
        echo "    Please run:"
        echo "    sudo apt update && sudo apt install -y python3-venv python3-pip python3-full"
        return 1
    fi
    echo "    [✓] Pip verified: $("$VENV_PYTHON" -m pip --version)"

    # 4. Install dependencies
    echo "[*] Step 4: Installing package dependencies..."
    "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
    fi
    "$VENV_PYTHON" -m pip install -e "$SCRIPT_DIR" --no-deps >/dev/null 2>&1 || true

    # 5. Create runtime directories
    mkdir -p "$SCRIPT_DIR/data/oui" "$SCRIPT_DIR/config" "$SCRIPT_DIR/exports"

    echo "======================================================================"
    echo "[✓] Environment repair and package sync completed successfully!"
    echo "======================================================================"
    return 0
}

# ------------------------------------------------------------------------------
# Handle explicit repair flags (--fix, --repair, --reinstall, --setup)
# ------------------------------------------------------------------------------
if [ "$1" = "--fix" ] || [ "$1" = "--repair" ] || [ "$1" = "--reinstall" ] || [ "$1" = "--setup" ]; then
    repair_environment
    echo "[*] Verifying repaired installation with diagnostics:"
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
    [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ] && VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
    "$VENV_PYTHON" -m application diag
    exit 0
fi

# ------------------------------------------------------------------------------
# Handle --help / -h
# ------------------------------------------------------------------------------
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Wireless Analyzer Platform - Kali Linux Passive Signal Observer"
    echo ""
    echo "Usage:"
    echo "  ./run.sh [options]               Launch dashboard & live observation (default: http://127.0.0.1:8000)"
    echo "  ./run.sh --mock                  Launch in simulation/mock mode (no wireless hardware required)"
    echo "  ./run.sh diag                    Run pre-flight hardware, library, and system diagnostics"
    echo "  ./run.sh export [options]        Export captured sessions (csv, json, debrief)"
    echo "  ./run.sh oui update              Download / update offline IEEE OUI database"
    echo "  ./run.sh --fix                   Self-heal/recreate virtual environment & fix broken dependencies"
    echo ""
    echo "Flags:"
    echo "  --fix, --repair                  Repair broken Python venv, missing pip, or missing packages"
    echo "  --mock                           Simulate wireless telemetry without requiring physical adapters"
    echo "  --host <ip>                      Dashboard host IP (default: 127.0.0.1)"
    echo "  --port <port>                    Dashboard port (default: 8000)"
    echo "  -i, --interface <iface>          Wi-Fi interface (e.g. wlan0, auto)"
    echo "  -b, --ble-interface <iface>      Bluetooth interface (e.g. hci0, auto)"
    echo "  --debug                          Enable verbose debug logging"
    echo ""
    exit 0
fi

# ------------------------------------------------------------------------------
# Locate and Validate Virtual Environment Python
# ------------------------------------------------------------------------------
VENV_PYTHON=""
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
fi

# Validate virtualenv health: check if python executes and required modules are present
NEED_REPAIR=0
if [ -z "$VENV_PYTHON" ] || [ ! -x "$VENV_PYTHON" ]; then
    echo "[*] Virtual environment (.venv) not found."
    NEED_REPAIR=1
else
    # Test if interpreter runs and can import core dependencies
    if ! "$VENV_PYTHON" -c "import sys, fastapi, pydantic, jinja2, uvicorn" >/dev/null 2>&1; then
        echo "[!] Virtual environment interpreter is broken, outdated, or missing core dependencies."
        NEED_REPAIR=1
    fi
fi

if [ "$NEED_REPAIR" -eq 1 ]; then
    echo "[*] Auto-repairing Python virtual environment now..."
    repair_environment || {
        echo "[!] Auto-repair failed. Try running: ./install.sh --fix"
        exit 1
    }
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
    [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ] && VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
fi

# ------------------------------------------------------------------------------
# Dispatch Execution
# ------------------------------------------------------------------------------
# If first argument is a recognized CLI subcommand (run, diag, export, oui, db), pass arguments directly.
# Otherwise, default to "run" with any options passed.
case "$1" in
    run|diag|export|oui|db)
        exec "$VENV_PYTHON" -m application "$@"
        ;;
    *)
        exec "$VENV_PYTHON" -m application run "$@"
        ;;
esac
