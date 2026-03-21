# IntentWatch - Start Frontend
# This script starts the Vite development server

Write-Host "Starting IntentWatch Frontend..." -ForegroundColor Cyan
Write-Host ""

# Navigate to frontend directory
Set-Location "Frontend"

# Check if node_modules exists
if (-Not (Test-Path ".\node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host ""
}

# Start the Vite dev server
Write-Host "Starting Vite dev server on http://localhost:5173..." -ForegroundColor Green
Write-Host ""
npm run dev
