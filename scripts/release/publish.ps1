# --------------------------------------------------------------
# Publish folder — aligned with .github/workflows/deploy.yml (job: package)
#
# Parity (local manual pack):
#   - Optional prelabeler regression (same command as CI)
#   - Asset version = Unix epoch seconds (CI: ASSET_VERSION from deploy_start_ts)
#   - Cache bust: only ui/*.html and ui/pages/*.html (sed-equivalent replace)
#   - Tree: mirror repo with same exclusions as "Build release tarball" tar step
#
# Usage: .\scripts\release\publish.ps1 [-SkipTests] [-NoPipInstall] [-AssetVersion "1736..."] [-CleanupAfter] [-VersionOnly]
# Resolves repo root from script location (works if cwd is not repo root).
# --------------------------------------------------------------

param(
    [string]$AssetVersion = "",
    [switch]$SkipTests,
    [switch]$NoPipInstall,
    [switch]$CleanupAfter,
    [switch]$VersionOnly
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PublishDir = Join-Path $RepoRoot "publish"

if ($VersionOnly) {
    Write-Host "Version-only: running build-version.js..." -ForegroundColor Yellow
    $bv = Join-Path $RepoRoot "build-version.js"
    if (-not (Test-Path $bv)) {
        Write-Host "Missing $bv" -ForegroundColor Red
        exit 1
    }
    Push-Location $RepoRoot
    try {
        & node $bv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
    Write-Host "Version build completed." -ForegroundColor Green
    exit 0
}

function Get-UnixEpochSeconds {
    [Math]::Floor([decimal]([DateTimeOffset]::UtcNow.UtcDateTime - [datetime]'1970-01-01T00:00:00Z').TotalSeconds)
}

function Invoke-CacheBustDeployParity {
    param([string]$Root, [string]$Version)
    # Mirrors: sed on ui/*.html and ui/pages/*.html only (deploy.yml "Apply cache-busting")
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $paths = @(
        (Join-Path $Root "ui"),
        (Join-Path $Root "ui\pages"),
        (Join-Path $Root "ui\pages\generated")
    )
    foreach ($dir in $paths) {
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem -Path $dir -Filter "*.html" -File -ErrorAction SilentlyContinue | ForEach-Object {
            $c = Get-Content $_.FullName -Raw -Encoding UTF8
            $c = $c -replace 'style\.css(\?v=\d+)?', "style.css?v=$Version"
            $c = $c -replace 'app\.js(\?v=\d+)?', "app.js?v=$Version"
            [System.IO.File]::WriteAllText($_.FullName, $c, $utf8)
        }
    }
}

function Test-RobocopySuccess {
    param([int]$ExitCode)
    # Robocopy: 0–7 = OK (MS docs)
    if ($ExitCode -ge 8) {
        throw "robocopy failed with exit code $ExitCode"
    }
}

Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "  Publish (CI parity: .github/workflows/deploy.yml package)"
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan

if (-not $AssetVersion) {
    $AssetVersion = "$(Get-UnixEpochSeconds)"
}
Write-Host "[info] ASSET_VERSION (epoch) = $AssetVersion" -ForegroundColor Gray

# 0 — Same tests as CI "Run prelabeler regression suite" (after deps installed on dev machine)
if (-not $SkipTests) {
    Write-Host "[0/4] Prelabeler regression (deploy.yml package job)..." -ForegroundColor Cyan
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "python not found on PATH. Install Python 3.11 or use -SkipTests."
    }
    $reqProd = Join-Path $RepoRoot "requirements-prod.txt"
    if (-not (Test-Path $reqProd)) {
        throw "Missing $reqProd"
    }
    if (-not $NoPipInstall) {
        Write-Host "  pip install -r requirements-prod.txt (same as CI)..." -ForegroundColor Gray
        & python -m pip install --no-cache-dir -r $reqProd
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed (exit $LASTEXITCODE)"
        }
        & python -m pip install --no-cache-dir -e $RepoRoot
        if ($LASTEXITCODE -ne 0) {
            throw "pip install -e . failed (exit $LASTEXITCODE)"
        }
    }
    else {
        Write-Host "  [skip] -NoPipInstall -- ensure deps match CI" -ForegroundColor Yellow
    }
    $env:PYTHONIOENCODING = "utf-8"
    $regScript = Join-Path $RepoRoot "scripts\labeling\run_prelabeler_labeling_cases.py"
    if (-not (Test-Path $regScript)) {
        throw "Missing $regScript"
    }
    & python $regScript --min-pass-rate 1.0
    if ($LASTEXITCODE -ne 0) {
        throw "Prelabeler regression failed (exit $LASTEXITCODE). Fix or use -SkipTests."
    }
    Write-Host "  [OK] Regression passed" -ForegroundColor Green
} else {
    Write-Host "[0/4] Skipped tests (-SkipTests)" -ForegroundColor Yellow
}

# 1 — Clean output dir
if (Test-Path $PublishDir) {
    Write-Host "[1/4] Removing old publish folder..."
    Remove-Item -Path $PublishDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PublishDir | Out-Null

# 2 — Mirror tree like "tar -czf" excludes (deploy.yml "Build release tarball")
Write-Host "[2/4] Mirroring repo into publish\ (tar exclusions)..." -ForegroundColor Cyan
$excludeDirs = @(".git", ".venv", "publish", "__pycache__")
$excludeFiles = @("*.pyc", "*.pyo", "*.log")
# robocopy: destination must exist; /E all subdirs; /XD /XF match CI intent
$robolog = Join-Path $env:TEMP "robocopy-publish.log"
$args = @(
    $RepoRoot, $PublishDir,
    "/E",
    "/NFL", "/NDL", "/NJH", "/NJS", "/NP"
)
foreach ($d in $excludeDirs) { $args += "/XD", $d }
foreach ($f in $excludeFiles) { $args += "/XF", $f }

& robocopy @args | Out-Null
Test-RobocopySuccess $LASTEXITCODE

# Optional: keep production env next to artifact (like old script; not in git on CI)
if (Test-Path (Join-Path $RepoRoot ".env")) {
    Copy-Item -Path (Join-Path $RepoRoot ".env") -Destination (Join-Path $PublishDir ".env") -Force
    Write-Host "  [OK] Copied .env into publish (local only; CI artifact uses repo checkout)" -ForegroundColor Green
} elseif (Test-Path (Join-Path $RepoRoot ".env.example")) {
    Copy-Item -Path (Join-Path $RepoRoot ".env.example") -Destination (Join-Path $PublishDir ".env.example") -Force
    Write-Host "  [INFO] Copied .env.example (no .env)" -ForegroundColor Gray
}

# 3 — Cache bust on *copies* only (under publish); matches CI sed scope
Write-Host "[3/4] Cache bust: publish\ui\*.html + publish\ui\pages\*.html (v=$AssetVersion)..." -ForegroundColor Cyan
Invoke-CacheBustDeployParity -Root $PublishDir -Version $AssetVersion
Write-Host "  [OK] HTML query strings updated" -ForegroundColor Green

# 4 — Done
Write-Host "[4/4] ------------------------------------------------------" -ForegroundColor Green
Write-Host "  PUBLISH READY: $PublishDir"
Write-Host "  VPS install (same as deploy job):"
Write-Host "    cd <release_dir>; python3 -m venv .venv; . .venv/bin/activate"
Write-Host "    pip install --upgrade pip"
Write-Host "    pip install --no-cache-dir -r requirements-prod.txt"
Write-Host "--------------------------------------------------------------" -ForegroundColor Green

if ($CleanupAfter) {
    Write-Host ""
    Write-Host "  [SECURITY] Cleanup in 30s (Ctrl+C to keep folder)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    Remove-Item -Path $PublishDir -Recurse -Force
    Write-Host "  Removed publish folder." -ForegroundColor Yellow
}
