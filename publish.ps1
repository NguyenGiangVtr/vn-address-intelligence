# Quick Publish Script - VN Address Intelligence
# Wrapper cho scripts/release/publish.ps1 voi versioning

param(
    [switch]$CleanupAfter,  # Xoa folder publish sau khi hoan thanh
    [switch]$VersionOnly    # Chi chay version build, khong publish
)

$ErrorActionPreference = "Stop"

Write-Host "VN Address Intelligence - Quick Publish" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Gray

if ($VersionOnly) {
    Write-Host "Chi chay version build..." -ForegroundColor Yellow
    
    if (Test-Path "build-version.js") {
        node build-version.js
    } else {
        Write-Host "build-version.js khong tim thay!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Version build hoan tat!" -ForegroundColor Green
    exit 0
}

# Check if main publish script exists
$mainScript = "scripts\release\publish.ps1"
if (-not (Test-Path $mainScript)) {
    Write-Host "Script publish chinh khong tim thay: $mainScript" -ForegroundColor Red
    exit 1
}

Write-Host "Dang chay publish voi versioning..." -ForegroundColor White

# Run main publish script
if ($CleanupAfter) {
    & $mainScript -CleanupAfter
} else {
    & $mainScript
}

Write-Host ""
Write-Host "Cach su dung nhanh:" -ForegroundColor White
Write-Host "  .\publish.ps1              - Build version + tao publish folder" -ForegroundColor Gray  
Write-Host "  .\publish.ps1 -CleanupAfter - Nhu tren + xoa folder sau 30s" -ForegroundColor Gray
Write-Host "  .\publish.ps1 -VersionOnly  - Chi chay version build" -ForegroundColor Gray