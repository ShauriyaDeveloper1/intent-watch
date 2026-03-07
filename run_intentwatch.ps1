$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $root "backend"
$frontendPath = Join-Path $root "Build AI Surveillance System"
$venvActivate = Join-Path $root "venv\Scripts\Activate.ps1"

$backendCmd = "& { Set-Location -Path `"$backendPath`"; & `"$venvActivate`"; & `"$root\venv\Scripts\python.exe`" -m uvicorn api.main:app --host 127.0.0.1 --port 8000 }"
Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd

$frontendCmd = "& { Set-Location -Path `"$frontendPath`"; if (!(Test-Path node_modules)) { npm install }; npm run dev }"
Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd
