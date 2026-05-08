# --------------------------------------------------------------
# Publish Script for VN Address Intelligence
# Create a clean 'publish' folder for VPS upload
# Usage: .\scripts\release\publish.ps1 [-CleanupAfter]
# --------------------------------------------------------------

param(
    [switch]$CleanupAfter  # Delete publish folder after completion (security)
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PublishDir = "publish"

Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "  Building Publish Folder with Versioning..."
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan

# 0. Run version build first (NEW)
Write-Host "[0/5] Updating versions for cache busting..."
try {
    $timestamp = Get-Date -Format "yyyyMMddHHmm"
    
    # Check if Node.js build script exists
    if (Test-Path "build-version.js") {
        Write-Host "  - Running Node.js build script..." -ForegroundColor Yellow
        node build-version.js
        Write-Host "  [OK] Version build completed: $timestamp" -ForegroundColor Green
    } else {
        # Fallback to PowerShell version
        Write-Host "  - Running PowerShell fallback..." -ForegroundColor Yellow
        $uiPath = "ui"
        if (Test-Path $uiPath) {
            $htmlFiles = Get-ChildItem -Path $uiPath -Filter "*.html" -Recurse
            foreach ($file in $htmlFiles) {
                $content = Get-Content $file.FullName -Raw -Encoding UTF8
                $content = $content -replace 'style\.css\?v=\d+', "style.css?v=$timestamp"
                $content = $content -replace 'app\.js(\?v=\d+)?', "app.js?v=$timestamp"
                Set-Content -Path $file.FullName -Value $content -Encoding UTF8
            }
            Write-Host "  [OK] Updated $($htmlFiles.Count) files with version: $timestamp" -ForegroundColor Green
        }
    }
} catch {
    Write-Warning "  [WARN] Version build failed: $($_.Exception.Message)"
    Write-Host "  Continuing publish..." -ForegroundColor Yellow
}

# 1. Clean old publish folder
if (Test-Path $PublishDir) {
    Write-Host "[1/5] Removing old publish folder..."
    Remove-Item -Path $PublishDir -Recurse -Force
}

# 2. Create directory structure
Write-Host "[2/5] Creating directory structure..."
New-Item -ItemType Directory -Path $PublishDir | Out-Null
$SubDirs = @("app", "ui", "data", "scripts", "models", "reports", "logs")
foreach ($dir in $SubDirs) {
    New-Item -ItemType Directory -Path "$PublishDir\$dir" | Out-Null
}

# 3. Copy files with versioned assets
Write-Host "[3/5] Copying files (excluding junk files)..."
Copy-Item -Path "app\*" -Destination "$PublishDir\app" -Recurse -Exclude "__pycache__", "*.pyc"
Copy-Item -Path "ui\*" -Destination "$PublishDir\ui" -Recurse
Copy-Item -Path "ui\login.html" -Destination "$PublishDir\ui" # Explicit copy
Copy-Item -Path "scripts\deployment\vnai-vps-setup.sh" -Destination "$PublishDir\scripts"
Copy-Item -Path "requirements.txt" -Destination "$PublishDir"
Copy-Item -Path "start.py" -Destination "$PublishDir"
# Copy actual .env file for production
if (Test-Path ".env") {
    Copy-Item -Path ".env" -Destination "$PublishDir"
    Write-Host "  [OK] Copied .env file" -ForegroundColor Green
} else {
    Copy-Item -Path ".env.example" -Destination "$PublishDir"
    Write-Warning "  [WARN] .env not found, using .env.example"
}

# Copy seed data only
if (Test-Path "data\seed") {
    New-Item -ItemType Directory -Path "$PublishDir\data\seed" | Out-Null
    Copy-Item -Path "data\seed\*" -Destination "$PublishDir\data\seed" -Recurse
}

# 4. Copy version info for reference
Write-Host "[4/5] Copying version info..."
if (Test-Path "version-info.json") {
    Copy-Item -Path "version-info.json" -Destination "$PublishDir"
    $versionInfo = Get-Content "version-info.json" | ConvertFrom-Json
    Write-Host "  [OK] Version: $($versionInfo.version) - Timestamp: $($versionInfo.timestamp)" -ForegroundColor Green
}

# 5. Success
Write-Host "--------------------------------------------------------------" -ForegroundColor Green
Write-Host "  [OK] PUBLISH FOLDER IS READY!"
Write-Host "  Location: $PWD\$PublishDir"
Write-Host "  "
if (Test-Path "version-info.json") {
    $versionInfo = Get-Content "version-info.json" | ConvertFrom-Json
    Write-Host "  Version: $($versionInfo.version)" -ForegroundColor Cyan
    Write-Host "  Build time: $($versionInfo.timestamp)" -ForegroundColor Gray
    Write-Host "  "
}
Write-Host "  You can zip the 'publish' folder and upload to your VPS,"
Write-Host "  or use MobaXterm to drag-and-drop content to /opt/vnai/"
Write-Host "  "
Write-Host "  CSS and JS were updated with a new version; browser cache will refresh." -ForegroundColor Yellow

# Optional cleanup for security
if ($CleanupAfter) {
    Write-Host "  "
    Write-Host "  [SECURITY] Auto-cleanup enabled. Folder will be deleted in 30 seconds..."
    Write-Host "  Press Ctrl+C to cancel cleanup."
    Start-Sleep -Seconds 30
    Remove-Item -Path $PublishDir -Recurse -Force
    Write-Host "  [OK] Publish folder cleaned up for security." -ForegroundColor Yellow
}

Write-Host "--------------------------------------------------------------" -ForegroundColor Green
