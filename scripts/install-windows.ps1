# Regia Installer for Windows
# Run: powershell -ExecutionPolicy Bypass -File install-windows.ps1

$ErrorActionPreference = "Stop"
$REGIA_DIR = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $REGIA_DIR) { $REGIA_DIR = Get-Location }

Write-Host ""
Write-Host "============================================" -ForegroundColor DarkYellow
Write-Host "       Regia Installer for Windows          " -ForegroundColor Yellow
Write-Host "   Intelligent Document Management System   " -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor DarkYellow
Write-Host ""

function Check-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

# === Check Python ===
Write-Host "[1/6] Checking Python..." -ForegroundColor Cyan
if (Check-Command "python") {
    $pyVer = python --version 2>&1
    Write-Host "  Found: $pyVer" -ForegroundColor Green
} else {
    Write-Host "  Python not found. Installing via winget..." -ForegroundColor Yellow
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    refreshenv
}

# === Check Node.js ===
Write-Host "[2/6] Checking Node.js..." -ForegroundColor Cyan
if (Check-Command "node") {
    $nodeVer = node --version 2>&1
    Write-Host "  Found: Node.js $nodeVer" -ForegroundColor Green
} else {
    Write-Host "  Node.js not found. Installing via winget..." -ForegroundColor Yellow
    winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
    refreshenv
}

# === Check Ollama (optional) ===
Write-Host "[3/6] Checking Ollama (AI engine)..." -ForegroundColor Cyan
if (Check-Command "ollama") {
    Write-Host "  Found: Ollama installed" -ForegroundColor Green
} else {
    Write-Host "  Ollama not found. Would you like to install it for AI features? (Y/n)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -ne "n" -and $answer -ne "N") {
        Write-Host "  Installing Ollama..." -ForegroundColor Yellow
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
        Write-Host "  Pulling lightweight AI model..." -ForegroundColor Yellow
        ollama pull qwen2.5:0.5b
    } else {
        Write-Host "  Skipped. Regia will use rule-based classification." -ForegroundColor DarkYellow
    }
}

# === Setup Backend ===
Write-Host "[4/6] Setting up backend..." -ForegroundColor Cyan
$backendDir = Join-Path $REGIA_DIR "backend"
if (-not (Test-Path (Join-Path $backendDir "venv"))) {
    python -m venv (Join-Path $backendDir "venv")
}
& (Join-Path $backendDir "venv\Scripts\pip") install -r (Join-Path $backendDir "requirements.txt") -q
Write-Host "  Backend dependencies installed" -ForegroundColor Green

# === Setup Frontend ===
Write-Host "[5/6] Setting up frontend..." -ForegroundColor Cyan
$frontendDir = Join-Path $REGIA_DIR "frontend"
Push-Location $frontendDir
npm install --silent
Pop-Location
Write-Host "  Frontend dependencies installed" -ForegroundColor Green

# === Create Start Script ===
Write-Host "[6/6] Creating start script..." -ForegroundColor Cyan
$startScript = @"
@echo off
title Regia - Document Intelligence
echo Starting Regia...
echo.

:: Start backend
cd /d "$backendDir"
start /b venv\Scripts\python run.py

:: Wait for backend
timeout /t 3 /nobreak > nul

:: Start frontend
cd /d "$frontendDir"
start /b npm run dev

:: Wait and open browser
timeout /t 2 /nobreak > nul
start http://localhost:5173

echo.
echo Regia is running!
echo   Backend:  http://localhost:8420
echo   Frontend: http://localhost:5173
echo.
echo Press Ctrl+C to stop.
pause > nul
"@
$startScript | Out-File -FilePath (Join-Path $REGIA_DIR "Start-Regia.bat") -Encoding ASCII

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Regia installed successfully!             " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Run 'Start-Regia.bat' to launch Regia"
Write-Host "  Or run 'npm run tauri:dev' in frontend/ for desktop mode"
Write-Host ""
