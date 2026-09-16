@echo off
REM Signal Observer - Windows Batch Runner Wrapper
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m application run %*
) else (
    python -m application run %*
)
