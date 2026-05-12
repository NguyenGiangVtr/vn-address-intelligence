# VN Address Intelligence — cache-bust query strings trong ui/**/*.html (Windows)
# Chạy từ repo: powershell -File scripts/release/build_ui_assets.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

Write-Host "VN Address Intelligence - Build UI assets (cache bust)" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Gray

$timestamp = Get-Date -Format "yyyyMMddHHmm"
Write-Host "Version: $timestamp" -ForegroundColor Yellow

$uiPath = Join-Path $RepoRoot "ui"
if (-not (Test-Path $uiPath)) {
    Write-Host "Missing ui/ under $RepoRoot" -ForegroundColor Red
    exit 1
}

$htmlFiles = Get-ChildItem -Path $uiPath -Filter "*.html" -Recurse
$updatedCount = 0

foreach ($file in $htmlFiles) {
    try {
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        $content = $content -replace 'style\.css\?v=\d+', "style.css?v=$timestamp"
        $content = $content -replace 'app\.js(\?v=\d+)?', "app.js?v=$timestamp"
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8
        $relativePath = $file.FullName.Replace($RepoRoot + [IO.Path]::DirectorySeparatorChar, "")
        Write-Host "  OK $relativePath" -ForegroundColor Green
        $updatedCount++
    } catch {
        Write-Host "  FAIL $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

$versionInfo = @{
    version     = $timestamp
    timestamp   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    files_updated = $updatedCount
} | ConvertTo-Json -Depth 2

Set-Content -Path (Join-Path $RepoRoot "version-info.json") -Value $versionInfo -Encoding UTF8

Write-Host "Done. Updated $updatedCount file(s)." -ForegroundColor Green
Write-Host "Tip: npm run build uses build-version.js (Node); this script is the PowerShell equivalent." -ForegroundColor Gray
