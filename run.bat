@echo off
REM Wireless Analyzer - Windows Batch Runner Wrapper
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"

if "%1"=="--fix" (
    echo [*] Repairing environment and dependencies...
    if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
        "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
        "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install -r requirements.txt
        "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install -e . --no-deps
    ) else (
        python -m venv .venv
        "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
        "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install -r requirements.txt
        "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install -e . --no-deps
    )
    echo [✓] Environment verified.
    exit /b 0
)

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m application %*
) else (
    python -m application %*
)
