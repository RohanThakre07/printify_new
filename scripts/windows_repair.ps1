param(
    [Parameter(Mandatory=$true)]
    [string]$FreshProjectPath,

    [string]$TargetPath = "C:\printify-automation"
)

$ErrorActionPreference = "Stop"

Write-Host "[  0%] Starting repair"
$sourceBackend = Join-Path $FreshProjectPath "backend"
$sourceLauncher = Join-Path $FreshProjectPath "run_server.py"
$sourceStarter = Join-Path $FreshProjectPath "scripts\start_windows.ps1"

if (-not (Test-Path $TargetPath)) { throw "Target folder not found: $TargetPath" }
if (-not (Test-Path $sourceBackend)) { throw "Fresh source missing: $sourceBackend" }
if (-not (Test-Path $sourceLauncher)) { throw "Fresh source missing: $sourceLauncher" }
if (-not (Test-Path $sourceStarter)) { throw "Fresh source missing: $sourceStarter" }

$targetBackend = Join-Path $TargetPath "backend"
Write-Host "[ 25%] Replacing backend folder with fresh copy"
if (Test-Path $targetBackend) {
    Remove-Item $targetBackend -Recurse -Force
}
New-Item -ItemType Directory -Path $targetBackend -Force | Out-Null
Copy-Item -Path (Join-Path $sourceBackend "*") -Destination $targetBackend -Recurse -Force

Write-Host "[ 55%] Copying launcher and starter script"
Copy-Item -Path $sourceLauncher -Destination (Join-Path $TargetPath "run_server.py") -Force
New-Item -ItemType Directory -Path (Join-Path $TargetPath "scripts") -Force | Out-Null
Copy-Item -Path $sourceStarter -Destination (Join-Path $TargetPath "scripts\start_windows.ps1") -Force

Write-Host "[ 70%] Verifying required files"
$required = @(
    (Join-Path $TargetPath "backend\app\main.py"),
    (Join-Path $TargetPath "backend\requirements.txt"),
    (Join-Path $TargetPath "run_server.py"),
    (Join-Path $TargetPath "scripts\start_windows.ps1")
)
foreach ($file in $required) {
    if (-not (Test-Path $file)) { throw "Missing after repair: $file" }
}

$python = Join-Path $TargetPath ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "[ 85%] Creating virtual environment"
    Set-Location $TargetPath
    python -m venv .venv
}

$python = Join-Path $TargetPath ".venv\Scripts\python.exe"
Write-Host "[ 90%] Installing backend requirements"
& $python -m pip install -r (Join-Path $TargetPath "backend\requirements.txt")

Write-Host "[100%] Repair finished"
Write-Host "Run next:"
Write-Host "  powershell -ExecutionPolicy Bypass -File $TargetPath\scripts\start_windows.ps1 -ProjectPath $TargetPath"
