# Full VNAI flow: regression -> (DB) audit -> (DB) experiment -> (DB) pipeline -> (HF) NER smoke -> LaTeX metrics
# Requires: repo root, PYTHONPATH=., pip deps, .env for DB steps.
# Usage (PowerShell):
#   cd "D:\2.GIT SOURCE\vn-address-intelligence"
#   .\scripts\flow\run_full_vnai_flow.ps1
#   .\scripts\flow\run_full_vnai_flow.ps1 -SkipTrain
#   .\scripts\flow\run_full_vnai_flow.ps1 -SkipDb
#   .\scripts\flow\run_full_vnai_flow.ps1 -OptionalDb   # DB down: skip experiment + pipeline after audit fails
#   .\scripts\flow\run_full_vnai_flow.ps1 -PipelineLimit 25

param(
    [switch] $SkipTrain,
    [switch] $SkipDb,
    [switch] $OptionalDb,
    [int] $PipelineLimit = 25,
    [string] $TrainOutputDir = "models/phobert-ner-vn-flow-last"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $Root "app"))) {
    $Root = (Get-Location).Path
}
Set-Location $Root
$env:PYTHONPATH = "."

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
}

function Invoke-PythonStep([string]$Name, [string[]]$Arguments) {
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    # Do not `return` exit code from this function: `& python` stdout would be collected
    # together with the return value when the caller does `$x = Invoke-PythonStep`, breaking
    # numeric exit checks. Start-Process breaks paths with spaces. Use script-scope exit.
    & python @Arguments
    $script:InvokePythonStepExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
}

New-Item -ItemType Directory -Force -Path "reports" | Out-Null

Invoke-Step "py_compile (critical modules)" {
    python -m py_compile `
        scripts/diagnostics/audit_acq_admin_bridge.py `
        scripts/flow/generate_scientific_report_metrics.py `
        app/ai/train_ner.py `
        app/ai/production_pipeline.py `
        app/ai/experiment_runner.py `
        app/ai/report_generator.py
}

Invoke-Step "PreLabeler labeling cases" {
    python scripts/labeling/run_prelabeler_labeling_cases.py
}

Invoke-Step "PreLabeler regression" {
    python scripts/test/test_prelabeler_regression.py
}

$auditJson = Join-Path $Root "reports/audit_acq_admin_bridge_last.json"
$trainLog = Join-Path (Join-Path $Root $TrainOutputDir) "training_log.json"
$expCsv = Join-Path $Root "reports/experiment_results.csv"

if (-not $SkipDb) {
    Invoke-PythonStep "audit_acq_admin_bridge + JSON" @(
        "scripts/diagnostics/audit_acq_admin_bridge.py",
        "--write-json",
        $auditJson
    )
    $auditExit = $script:InvokePythonStepExitCode
    if ($auditExit -ne 0) {
        $msg = "audit_acq_admin_bridge exited $auditExit (often: PostgreSQL unreachable - check .env DB_HOST/port or VPN)."
        if ($OptionalDb) {
            Write-Host ""
            Write-Host "WARN: $msg" -ForegroundColor Yellow
            Write-Host "Skipping experiment_runner and production_pipeline (OptionalDb)." -ForegroundColor Yellow
        } else {
            throw ($msg + " Use -SkipDb (no DB) or -OptionalDb (continue without DB steps).")
        }
    } else {
        Invoke-Step "experiment_runner (no LLM)" {
            python -m app.ai.experiment_runner --config app/ai/config.yaml --no-llm
        }
        Invoke-Step "production_pipeline (pilot)" {
            python app/ai/production_pipeline.py --config app/ai/config.yaml --limit $PipelineLimit
        }
    }
} else {
    Write-Host "`n=== Skipping DB steps (audit / experiment / pipeline) ===" -ForegroundColor Yellow
}

if (-not $SkipTrain) {
    Invoke-Step "train_ner HF smoke (needs network + torch)" {
        python app/ai/train_ner.py `
            --hf-dataset dathuynh1108/ner-address-standard-dataset `
            --hf-max-train 4000 `
            --hf-max-eval 800 `
            --epochs 1 `
            --batch-size 8 `
            --output $TrainOutputDir
    }
} else {
    Write-Host "`n=== Skipping NER train (use existing training_log if any) ===" -ForegroundColor Yellow
}

Invoke-Step "generate_scientific_report_metrics.tex" {
    $tlArg = @()
    if (Test-Path $trainLog) { $tlArg = @("--training-log", $trainLog) }
    $ajArg = @()
    if (Test-Path $auditJson) { $ajArg = @("--audit-json", $auditJson) }
    $ecArg = @()
    if (Test-Path $expCsv) { $ecArg = @("--experiment-csv", $expCsv) }
    python scripts/flow/generate_scientific_report_metrics.py @tlArg @ajArg @ecArg
}

Write-Host "`nDone. Next: xelatex docs/scientific-report/vnai-chapters-master.tex" -ForegroundColor Green
