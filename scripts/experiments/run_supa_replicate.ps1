# SUPA-Bench — lặp lại nhiều lần (seed sweep hoặc repeat) + tùy chọn retention
# Mặc định: 20 run, sweep-seed (base seed ngẫu nhiên mỗi lần gọi script nếu không truyền -SeedStart), N=1000, oracle demo.
#
# Ví dụ pipeline thật (cần file preds đã điền + source-note):
#   .\scripts\experiments\run_supa_replicate.ps1 -N 1000 -NRuns 20 -PredsCsv reports\supa_preds_batch.csv -SourceNote "checkpoint=..."

param(
    [int] $NRuns = 20,
    [ValidateSet("sweep-seed", "repeat-determinism")]
    [string] $Mode = "sweep-seed",
    [Nullable[int]] $SeedStart = $null,
    [int] $Seed = 42,
    [int] $N = 1000,
    [string] $NoiseProfile = "SUP-1.0.0",
    [int] $Retention = 0,
    [switch] $DemoPredsCopyRef,
    [string] $PredsCsv = "",
    [string] $SourceNote = "",
    [switch] $SkipImport,
    [switch] $ExportTexLast
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $Root "scripts\experiments\supa_benchmark.py"))) {
    $Root = (Get-Location).Path
}
Set-Location $Root
$env:PYTHONPATH = ".;$Root\src"

$supa = "scripts/experiments/supa_benchmark.py"
$argsList = @(
    "replicate",
    "--n-runs", "$NRuns",
    "--mode", $Mode,
    "--n", "$N",
    "--noise-profile", $NoiseProfile,
    "--retention", "$Retention",
    "--specimens-out", "reports/supa_workflow_specimens_latest.csv"
)
if ($Mode -eq "sweep-seed") {
    if ($null -ne $SeedStart) { $argsList += @("--seed-start", "$SeedStart") }
} else {
    $argsList += @("--seed", "$Seed")
}

if ($DemoPredsCopyRef) {
    if ($PredsCsv) { throw "Use either -DemoPredsCopyRef or -PredsCsv, not both." }
    $argsList += "--preds-demo-ref-v2"
}
elseif ($PredsCsv) {
    $argsList += @("--preds", $PredsCsv)
    if (-not $SourceNote) { throw "-PredsCsv requires -SourceNote." }
    $argsList += @("--source-note", $SourceNote)
}
elseif ($SkipImport) {
    $argsList += "--skip-import"
}
else {
    throw "Specify -DemoPredsCopyRef (smoke), or -PredsCsv + -SourceNote, or -SkipImport."
}

if ($ExportTexLast) { $argsList += "--export-tex-last" }

Write-Host ">>> python $supa $($argsList -join ' ')" -ForegroundColor Cyan
& python $supa @argsList
exit $LASTEXITCODE
