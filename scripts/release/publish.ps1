# --------------------------------------------------------------
# Publish Script for VN Address Intelligence
# Tao mot thu muc 'publish' sach de upload len VPS
# Usage: .\scripts\release\publish.ps1 [-CleanupAfter]
# --------------------------------------------------------------

param(
    [switch]$CleanupAfter  # Xóa folder publish sau khi hoàn thành (bảo mật)
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PublishDir = "publish"

Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "  Building Publish Folder..."
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan

# 1. Clean old publish folder
if (Test-Path $PublishDir) {
    Write-Host "[1/4] Dang xoa thu muc publish cu..."
    Remove-Item -Path $PublishDir -Recurse -Force
}

# 2. Create directory structure
Write-Host "[2/4] Dang tao cau truc thu muc..."
New-Item -ItemType Directory -Path $PublishDir | Out-Null
$SubDirs = @("app", "ui", "data", "scripts", "models", "reports", "logs")
foreach ($dir in $SubDirs) {
    New-Item -ItemType Directory -Path "$PublishDir\$dir" | Out-Null
}

# 3. Copy files
Write-Host "[3/4] Dang copy files (dang loai bo file rac)..."
Copy-Item -Path "app\*" -Destination "$PublishDir\app" -Recurse -Exclude "__pycache__", "*.pyc"
Copy-Item -Path "ui\*" -Destination "$PublishDir\ui" -Recurse
Copy-Item -Path "ui\login.html" -Destination "$PublishDir\ui" # Explicit copy
Copy-Item -Path "scripts\deployment\vnai-vps-setup.sh" -Destination "$PublishDir\scripts"
Copy-Item -Path "requirements.txt" -Destination "$PublishDir"
Copy-Item -Path "start.py" -Destination "$PublishDir"
# Copy actual .env file for production
if (Test-Path ".env") {
    Copy-Item -Path ".env" -Destination "$PublishDir"
    Write-Host "  ✅ Copied .env file" -ForegroundColor Green
} else {
    Copy-Item -Path ".env.example" -Destination "$PublishDir"
    Write-Warning "  ⚠️  .env not found, using .env.example"
}

# Copy seed data only
if (Test-Path "data\seed") {
    New-Item -ItemType Directory -Path "$PublishDir\data\seed" | Out-Null
    Copy-Item -Path "data\seed\*" -Destination "$PublishDir\data\seed" -Recurse
}

# 4. Success
Write-Host "--------------------------------------------------------------" -ForegroundColor Green
Write-Host "  [OK] THU MUC PUBLISH DA SAN SANG!"
Write-Host "  Vi tri: $PWD\$PublishDir"
Write-Host "  "
Write-Host "  Ban co the nen thu muc 'publish' lai va upload len VPS,"
Write-Host "  hoac dung MobaXterm keo tha noi dung trong 'publish' vao /opt/vnai/"

# Optional cleanup for security
if ($CleanupAfter) {
    Write-Host "  "
    Write-Host "  [SECURITY] Auto-cleanup enabled. Folder will be deleted in 30 seconds..."
    Write-Host "  Press Ctrl+C to cancel cleanup."
    Start-Sleep -Seconds 30
    Remove-Item -Path $PublishDir -Recurse -Force
    Write-Host "  ✅ Publish folder cleaned up for security." -ForegroundColor Yellow
}

Write-Host "--------------------------------------------------------------" -ForegroundColor Green
