param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptRoot

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$Action
    )
    Write-Host "`n[Regia Desktop Build] $Title"
    & $Action
}

Invoke-Step "Ensure frontend production bundle" {
    if (-not $SkipFrontendBuild) {
        Push-Location "$root\frontend"
        npm install --legacy-peer-deps | Out-Null
        npm run build
        Pop-Location
    } else {
        Write-Host "Skipping frontend build (--SkipFrontendBuild). Ensure frontend/dist exists."
    }
}

Invoke-Step "Install backend dependencies" {
    Push-Location "$root\backend"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python -m pip install -r requirements-dev.txt
    Pop-Location
}

Invoke-Step "Bundle backend with PyInstaller" {
    Push-Location "$root\backend"
    $distDir = Join-Path (Get-Location) 'dist'
    if (Test-Path "$distDir\regia-backend.exe") {
        Remove-Item "$distDir\regia-backend.exe" -Force
    }
    python -m PyInstaller `
        --noconfirm `
        --onefile `
        --name regia-backend `
        --hidden-import pkg_resources `
        --add-data "..\frontend\dist;frontend-dist" `
        --add-data "app\config\config.example.json;config" `
        run.py
    Pop-Location
}

Invoke-Step "Copy backend executable into Tauri resources" {
    $exeSource = "$root\backend\dist\regia-backend.exe"
    if (-not (Test-Path $exeSource)) {
        throw "Backend executable not found at $exeSource"
    }
    $resourceDir = "$root\frontend\src-tauri\resources"
    if (-not (Test-Path $resourceDir)) {
        New-Item -ItemType Directory -Path $resourceDir | Out-Null
    }
    Copy-Item $exeSource -Destination (Join-Path $resourceDir 'regia-backend.exe') -Force
}

Write-Host "`nRegia desktop backend build complete. You can now run 'npm run tauri:build' from frontend/."
