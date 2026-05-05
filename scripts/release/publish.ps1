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
Write-Host "  Building Publish Folder with Versioning..."
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan

# 0. Run version build first (NEW)
Write-Host "[0/5] Đang cập nhật versions cho cache busting..."
try {
    $timestamp = Get-Date -Format "yyyyMMddHHmm"
    
    # Check if Node.js build script exists
    if (Test-Path "build-version.js") {
        Write-Host "  • Chạy Node.js build script..." -ForegroundColor Yellow
        node build-version.js
        Write-Host "  ✅ Version build thành công với version: $timestamp" -ForegroundColor Green
    } else {
        # Fallback to PowerShell version
        Write-Host "  • Chạy PowerShell fallback..." -ForegroundColor Yellow
        $uiPath = "ui"
        if (Test-Path $uiPath) {
            $htmlFiles = Get-ChildItem -Path $uiPath -Filter "*.html" -Recurse
            foreach ($file in $htmlFiles) {
                $content = Get-Content $file.FullName -Raw -Encoding UTF8
                $content = $content -replace 'style\.css\?v=\d+', "style.css?v=$timestamp"
                $content = $content -replace 'app\.js(\?v=\d+)?', "app.js?v=$timestamp"
                Set-Content -Path $file.FullName -Value $content -Encoding UTF8
            }
            Write-Host "  ✅ Đã cập nhật $($htmlFiles.Count) files với version: $timestamp" -ForegroundColor Green
        }
    }
} catch {
    Write-Warning "  ⚠️  Lỗi khi build version: $($_.Exception.Message)"
    Write-Host "  Tiếp tục với publish..." -ForegroundColor Yellow
}

# 1. Clean old publish folder
if (Test-Path $PublishDir) {
    Write-Host "[1/5] Đang xóa thư mục publish cũ..."
    Remove-Item -Path $PublishDir -Recurse -Force
}

# 2. Create directory structure
Write-Host "[2/5] Đang tạo cấu trúc thư mục..."
New-Item -ItemType Directory -Path $PublishDir | Out-Null
$SubDirs = @("app", "ui", "data", "scripts", "models", "reports", "logs")
foreach ($dir in $SubDirs) {
    New-Item -ItemType Directory -Path "$PublishDir\$dir" | Out-Null
}

# 3. Copy files with versioned assets
Write-Host "[3/5] Đang copy files (đã loại bỏ file rác)..."
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

# 4. Copy version info for reference
Write-Host "[4/5] Đang copy thông tin version..."
if (Test-Path "version-info.json") {
    Copy-Item -Path "version-info.json" -Destination "$PublishDir"
    $versionInfo = Get-Content "version-info.json" | ConvertFrom-Json
    Write-Host "  ✅ Version: $($versionInfo.version) - Timestamp: $($versionInfo.timestamp)" -ForegroundColor Green
}

# 5. Success
Write-Host "--------------------------------------------------------------" -ForegroundColor Green
Write-Host "  [OK] THƯ MỤC PUBLISH ĐÃ SẴN SÀNG!"
Write-Host "  Vị trí: $PWD\$PublishDir"
Write-Host "  "
if (Test-Path "version-info.json") {
    $versionInfo = Get-Content "version-info.json" | ConvertFrom-Json
    Write-Host "  Version: $($versionInfo.version)" -ForegroundColor Cyan
    Write-Host "  Build time: $($versionInfo.timestamp)" -ForegroundColor Gray
    Write-Host "  "
}
Write-Host "  Bạn có thể nén thư mục 'publish' lại và upload lên VPS,"
Write-Host "  hoặc dùng MobaXterm kéo thả nội dung trong 'publish' vào /opt/vnai/"
Write-Host "  "
Write-Host "  CSS & JS da duoc update voi version moi - browser se tu refresh!" -ForegroundColor Yellow

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
