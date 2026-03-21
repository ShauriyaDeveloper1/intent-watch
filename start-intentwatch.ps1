# IntentWatch - Complete Application Startup Script
# This script starts both the backend and frontend servers

$ErrorActionPreference = "Continue"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  IntentWatch AI Surveillance System" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if both directories exist
if (-Not (Test-Path ".\backend")) {
    Write-Host "Error: Backend directory not found!" -ForegroundColor Red
    exit 1
}

if (-Not (Test-Path ".\Frontend")) {
    Write-Host "Error: Frontend directory not found!" -ForegroundColor Red
    exit 1
}

# Function to start backend in new window
function Start-Backend {
    Write-Host "Starting Backend Server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-backend.ps1"
}

# Function to start frontend in new window
function Start-Frontend {
    Write-Host "Starting Frontend Development Server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-frontend.ps1"
}

# Start both servers
Start-Backend
Start-Sleep -Seconds 3
Start-Frontend

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  IntentWatch is starting up!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Both servers are running in separate windows." -ForegroundColor Yellow
Write-Host "Close those windows to stop the servers." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
