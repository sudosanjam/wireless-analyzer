# Wireless Analyzer - Windows PowerShell Runner
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$SrcPath = Join-Path $ScriptDir 'src'
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = $SrcPath + ';' + $env:PYTHONPATH
} else {
    $env:PYTHONPATH = $SrcPath
}

if ($args -contains '--fix' -or $args -contains '--repair') {
    Write-Host '[*] Repairing virtual environment and dependencies...' -ForegroundColor Cyan
    $VenvPy = Join-Path $ScriptDir '.venv\Scripts\python.exe'
    if (-Not (Test-Path $VenvPy)) {
        & python -m venv .venv
    }
    & $VenvPy -m pip install --upgrade pip setuptools wheel
    & $VenvPy -m pip install -r requirements.txt
    & $VenvPy -m pip install -e . --no-deps
    Write-Host '[✓] Environment verified.' -ForegroundColor Green
    exit 0
}

$PythonExe = Join-Path $ScriptDir '.venv\Scripts\python.exe'
if (-Not (Test-Path $PythonExe)) {
    $PythonExe = 'python'
}

& $PythonExe -m application @args
