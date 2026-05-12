# SUPA-Bench — K lần chạy độc lập với cohort phân tầng D1–D4 (mặc định K=5, N=2000, oracle demo).
# Cần migration: scripts/migration/20260513_supa_stratified_specimen_and_ath_summary.sql
#
# Pipeline thật: -PredsCsv + -SourceNote (bỏ -DemoPredsCopyRef).
# Sau khi chạy: aggregate-runs --from-batch-json reports/supa_benchmark_last_batch_range.json --persist-ath

param(
    [int] $KRuns = 5,
    [int] $N = 2000,
    [Nullable[int]] $BaseSeed = $null,
    [string] $StratVersion = "strat-v1",
    [int] $MaxPoolRows = 100000,
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
    "replicate-stratified",
    "--k-runs", "$KRuns",
    "--n", "$N",
    "--strat-version", $StratVersion,
    "--max-pool-rows", "$MaxPoolRows",
    "--retention", "$Retention",
    "--specimens-out", "reports/supa_workflow_specimens_latest.csv"
)
if ($null -ne $BaseSeed) { $argsList += @("--base-seed", "$BaseSeed") }

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
