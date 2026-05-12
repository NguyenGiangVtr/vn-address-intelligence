# Khởi tạo bảng DB — chạy từ bất kỳ cwd; canonical: scripts/sql/create_tables.py
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $RepoRoot
try {
    & python (Join-Path $RepoRoot "scripts\sql\create_tables.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
