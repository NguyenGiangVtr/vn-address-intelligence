# VN Address Intelligence Build Script
# Tự động cập nhật version cho CSS & JS cache busting

Write-Host "🚀 VN Address Intelligence - Build Script" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Gray

# Check if Node.js is available
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js detected: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js không được tìm thấy. Vui lòng cài đặt Node.js" -ForegroundColor Red
    exit 1
}

# Generate version (current timestamp)
$timestamp = Get-Date -Format "yyyyMMddHHmm"
Write-Host "📦 Version: $timestamp" -ForegroundColor Yellow

# Update HTML files
Write-Host "`n📝 Đang cập nhật files..." -ForegroundColor White

$uiPath = Join-Path $PSScriptRoot "ui"
if (-not (Test-Path $uiPath)) {
    Write-Host "❌ Thư mục ui không tìm thấy!" -ForegroundColor Red
    exit 1
}

$htmlFiles = Get-ChildItem -Path $uiPath -Filter "*.html" -Recurse
$updatedCount = 0

foreach ($file in $htmlFiles) {
    try {
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        
        # Update CSS versions
        $content = $content -replace 'style\.css\?v=\d+', "style.css?v=$timestamp"
        
        # Update JS versions  
        $content = $content -replace 'app\.js(\?v=\d+)?', "app.js?v=$timestamp"
        
        # Write back
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8
        
        $relativePath = $file.FullName.Replace($PSScriptRoot + "\", "")
        Write-Host "  ✓ $relativePath" -ForegroundColor Green
        $updatedCount++
        
    } catch {
        Write-Host "  ❌ Lỗi: $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Save version info
$versionInfo = @{
    version = $timestamp
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    files_updated = $updatedCount
} | ConvertTo-Json -Depth 2

Set-Content -Path (Join-Path $PSScriptRoot "version-info.json") -Value $versionInfo -Encoding UTF8

Write-Host "`n✅ Build hoàn tất!" -ForegroundColor Green
Write-Host "📊 Đã cập nhật $updatedCount files với version $timestamp" -ForegroundColor Cyan
Write-Host "🌐 UI sẽ tự động load assets mới khi refresh browser" -ForegroundColor Yellow

Write-Host "`n💡 Sử dụng:" -ForegroundColor White  
Write-Host "  • npm run build     - Chạy build script" -ForegroundColor Gray
Write-Host "  • npm run publish   - Build + deploy" -ForegroundColor Gray
Write-Host "  • ./build.ps1       - Chạy trực tiếp script này" -ForegroundColor Gray