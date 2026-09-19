#!/usr/bin/env bash
# ==============================================================================
# Wireless Analyzer Platform - Runner Script
# Automatically resolves Python virtual environment and launches application
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON=""

# Locate virtual environment python
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    VENV_PYTHON=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
    VENV_PYTHON=$(command -v python)
else
    echo "[!] ERROR: No Python interpreter found. Please run ./install.sh first."
    exit 1
fi

# Execute application module
exec "$VENV_PYTHON" -m application run "$@"
