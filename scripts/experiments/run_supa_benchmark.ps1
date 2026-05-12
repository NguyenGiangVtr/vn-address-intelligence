# SUPA-Bench — chạy demo / kiểm thử lặp lại (PowerShell)
#
# Bước 0 (một lần trên DB, không cần psql):
#   python scripts/sql/apply_sql_file.py scripts/migration/20260209_prq_supa_benchmark_tables.sql
#
# Tham số mẫu:
#   .\scripts\experiments\run_supa_benchmark.ps1 -N 500                    # cohort ngẫu nhiên mỗi lần (không truyền -Seed)
#   .\scripts\experiments\run_supa_benchmark.ps1 -N 500 -Seed 7          # cohort cố định (tái lập)
#   .\scripts\experiments\run_supa_benchmark.ps1 -SkipExtract -RunId 12 -PredsCsv reports\supa_preds.csv -SourceNote "demo"
#   .\scripts\experiments\run_supa_benchmark.ps1 -SkipExtract -RunId 1 -DemoPredsCopyRef   # oracle smoke (--preds-demo-ref-v2)

param(
    [int] $N = 1000,
    [Nullable[int]] $Seed = $null,
    [string] $NoiseProfile = "SUP-1.0.0",
    [switch] $SkipExtract,
    [int] $RunId = 0,
    [string] $PredsCsv = "",
    [string] $SourceNote = "",
    [switch] $DemoPredsCopyRef,
    [string] $SpecimensOut = "reports/supa_workflow_specimens_latest.csv"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $Root "scripts\experiments\supa_benchmark.py"))) {
    if (-not (Test-Path (Join-Path $Root "src\app"))) {
        $Root = (Get-Location).Path
    }
}
Set-Location $Root
$env:PYTHONPATH = ".;$Root\src"

$supa = "scripts/experiments/supa_benchmark.py"
$argsList = @(
    "workflow",
    "--n", "$N",
    "--noise-profile", $NoiseProfile,
    "--specimens-out", $SpecimensOut
)
if ($null -ne $Seed) {
    $argsList += @("--seed", "$Seed")
}

if ($SkipExtract) {
    $argsList += @("--skip-extract")
    if ($RunId -gt 0) {
        $argsList += @("--run-id", "$RunId")
    }
}
if ($DemoPredsCopyRef) {
    if ($PredsCsv) {
        throw "Use either -DemoPredsCopyRef or -PredsCsv, not both."
    }
    $argsList += @("--preds-demo-ref-v2")
}
elseif ($PredsCsv) {
    $argsList += @("--preds", $PredsCsv)
    if (-not $SourceNote) {
        throw "PredsCsv requires -SourceNote for scientific provenance."
    }
    $argsList += @("--source-note", $SourceNote)
}

Write-Host ">>> python $supa $($argsList -join ' ')" -ForegroundColor Cyan
& python $supa @argsList
exit $LASTEXITCODE
