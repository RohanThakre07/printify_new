param(
    [string]$ProjectPath = "C:\printify-automation"
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectPath

$venvPython = Join-Path $ProjectPath ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ 10%] Creating virtual environment..."
    python -m venv .venv
}

$venvPython = Join-Path $ProjectPath ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Could not create/find venv python at $venvPython"
}

$requirements = Join-Path $ProjectPath "backend\requirements.txt"
if (-not (Test-Path $requirements)) {
    throw "Missing $requirements"
}

$mainFile = Join-Path $ProjectPath "backend\app\main.py"
if (-not (Test-Path $mainFile)) {
    throw "Missing $mainFile. Run windows_repair.ps1 with a fresh project copy first."
}

Write-Host "[ 40%] Installing dependencies..."
& $venvPython -m pip install -r $requirements

Write-Host "[ 70%] Starting app on http://127.0.0.1:8000"
Write-Host "[100%] Keep this window open while using the app"
& $venvPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
