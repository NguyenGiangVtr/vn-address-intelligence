# Quick Publish Script - VN Address Intelligence
# Wrapper for scripts/release/publish.ps1 with versioning

param(
    [switch]$CleanupAfter,  # Delete publish folder after completion
    [switch]$VersionOnly    # Run version build only, no publish
)

$ErrorActionPreference = "Stop"

Write-Host "VN Address Intelligence - Quick Publish" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Gray

if ($VersionOnly) {
    Write-Host "Running version build only..." -ForegroundColor Yellow
    
    if (Test-Path "build-version.js") {
        node build-version.js
    } else {
        Write-Host "build-version.js not found!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Version build completed." -ForegroundColor Green
    exit 0
}

# Check if main publish script exists
$mainScript = "scripts\release\publish.ps1"
if (-not (Test-Path $mainScript)) {
    Write-Host "Main publish script not found: $mainScript" -ForegroundColor Red
    exit 1
}

Write-Host "Running publish with versioning..." -ForegroundColor White

# Run main publish script
if ($CleanupAfter) {
    & $mainScript -CleanupAfter
} else {
    & $mainScript
}

Write-Host ""
Write-Host "Quick usage:" -ForegroundColor White
Write-Host "  .\publish.ps1               - Build version + create publish folder" -ForegroundColor Gray  
Write-Host "  .\publish.ps1 -CleanupAfter - Same as above + delete folder after 30s" -ForegroundColor Gray
Write-Host "  .\publish.ps1 -VersionOnly  - Run version build only" -ForegroundColor Gray