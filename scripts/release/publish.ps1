# --------------------------------------------------------------
# Publish Script for VN Address Intelligence
# Tao mot thu muc 'publish' sach de upload len VPS
# Usage: .\scripts\release\publish.ps1
# --------------------------------------------------------------

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
Copy-Item -Path ".env.example" -Destination "$PublishDir"

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
Write-Host "--------------------------------------------------------------" -ForegroundColor Green
