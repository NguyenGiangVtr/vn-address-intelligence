# ============================================================================
# ABLATION STUDY - Automated Wrapper Script
# ============================================================================
# Mục tiêu: Đo lường đóng góp của từng thành phần (NER, Retrieval, LLM)
# trong kiến trúc Hybrid SOTA
#
# Cấu hình thực nghiệm:
#   A1 (Full)           : NER + mGTE + LLM
#   A2 (No-LLM)         : NER + mGTE
#   A3 (Retrieval-only) : mGTE only
#   A4 (NER + LLM)      : NER + LLM (no retrieval)
#   A5 (Compare)        : NER + PhoBERT Siamese + LLM
#
# Usage:
#   .\scripts\experiments\run_ablation_study.ps1
#   .\scripts\experiments\run_ablation_study.ps1 -N 500 -Seed 777
#   .\scripts\experiments\run_ablation_study.ps1 -SkipExtract -RunId 10
# ============================================================================

param(
    [int] $N = 1000,
    [int] $Seed = 999,
    [string] $NoiseProfile = "SUP-1.0.0",
    [string] $ConfigPath = "app/ai/config.yaml",
    [switch] $SkipExtract,
    [int] $RunId = 0,
    [switch] $SkipA1,
    [switch] $SkipA2,
    [switch] $SkipA3,
    [switch] $SkipA4,
    [switch] $SkipA5
)

$ErrorActionPreference = "Stop"
$Root = "d:\2.GIT SOURCE\vn-address-intelligence"
Set-Location $Root
$env:PYTHONPATH = ".;$Root\src"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

function Save-Evidence {
    param(
        [string]$SourceFile,
        [string]$DestPath
    )
    if (Test-Path $SourceFile) {
        Copy-Item $SourceFile $DestPath -Force
        Write-Success "Saved evidence: $DestPath"
    } else {
        Write-Error-Custom "Evidence file not found: $SourceFile"
    }
}

# ============================================================================
# STEP 1: Extract Cohort (if not skipped)
# ============================================================================

if (-not $SkipExtract) {
    Write-Step "STEP 1: Extracting Ablation Cohort (N=$N, Seed=$Seed)"
    
    $extractArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "extract",
        "--n", "$N",
        "--seed", "$Seed",
        "--noise-profile", $NoiseProfile,
        "--notes", "Ablation Study cohort - baseline noise"
    )
    
    Write-Host ">>> python $($extractArgs -join ' ')" -ForegroundColor Yellow
    & python @extractArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Extract failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    
    # Get run_id from last_run_id.txt
    $runIdFile = "reports/supa_benchmark_last_run_id.txt"
    if (Test-Path $runIdFile) {
        $RunId = [int](Get-Content $runIdFile).Trim()
        Write-Success "Cohort extracted successfully. Run ID: $RunId"
    } else {
        Write-Error-Custom "Could not find run_id file"
        exit 1
    }
    
    # Export specimens
    Write-Host "`nExporting specimens..." -ForegroundColor Yellow
    $exportArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "export-specimens",
        "--out", "reports/ablation_specimens_baseline.csv"
    )
    & python @exportArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Export specimens failed"
        exit $LASTEXITCODE
    }
    
    # Save evidence
    Save-Evidence "reports/ablation_specimens_baseline.csv" "evidence/ablation/csv/specimens.csv"
    Save-Evidence "reports/supa_benchmark_last_run_id.txt" "evidence/ablation/run_id.txt"
    
    Write-Success "STEP 1 completed. Specimens saved to evidence/ablation/csv/"
} else {
    Write-Step "STEP 1: Skipped (using existing Run ID: $RunId)"
    if ($RunId -eq 0) {
        Write-Error-Custom "Must provide -RunId when using -SkipExtract"
        exit 1
    }
}

# ============================================================================
# STEP 2: Run Pipeline for Each Configuration
# ============================================================================

Write-Step "STEP 2: Running Pipeline for 5 Configurations"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$configs = @(
    @{
        Name = "A1"
        Description = "Full (NER + mGTE + LLM)"
        Args = @()
        Skip = $SkipA1
    },
    @{
        Name = "A2"
        Description = "No-LLM (NER + mGTE)"
        Args = @("--no-llm")
        Skip = $SkipA2
    },
    @{
        Name = "A3"
        Description = "Retrieval-only (mGTE)"
        Args = @("--no-ner", "--no-llm", "--retriever-type", "mgte")
        Skip = $SkipA3
    },
    @{
        Name = "A4"
        Description = "NER + LLM (no retrieval)"
        Args = @("--no-retrieval")
        Skip = $SkipA4
    },
    @{
        Name = "A5"
        Description = "PhoBERT Siamese (NER + PhoBERT + LLM)"
        Args = @("--retriever-type", "phobert")
        Skip = $SkipA5
    }
)

foreach ($config in $configs) {
    if ($config.Skip) {
        Write-Host "`n[SKIP] Configuration $($config.Name): $($config.Description)" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "`n----------------------------------------" -ForegroundColor Cyan
    Write-Host "Running Configuration $($config.Name): $($config.Description)" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    
    $outputCsv = "reports/ablation_preds_$($config.Name)_$timestamp.csv"
    $logFile = "evidence/ablation/logs/$($config.Name)_pipeline_$timestamp.log"
    
    $pipelineArgs = @(
        "src/app/ai/production_pipeline.py",
        "--config", $ConfigPath,
        "--supa-run-id", "$RunId",
        "--limit", "$N",
        "--output-csv", $outputCsv
    ) + $config.Args
    
    Write-Host ">>> python $($pipelineArgs -join ' ')" -ForegroundColor Yellow
    
    # Run pipeline and capture output
    $output = & python @pipelineArgs 2>&1 | Tee-Object -FilePath $logFile
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Pipeline failed for $($config.Name)"
        Write-Host "Check log: $logFile" -ForegroundColor Red
        continue
    }
    
    # Verify output
    if (Test-Path $outputCsv) {
        $lineCount = (Get-Content $outputCsv | Measure-Object -Line).Lines - 1  # Exclude header
        Write-Success "Configuration $($config.Name) completed. Output: $lineCount rows"
        
        # Save evidence
        Save-Evidence $outputCsv "evidence/ablation/csv/preds_$($config.Name).csv"
    } else {
        Write-Error-Custom "Output CSV not found for $($config.Name)"
    }
}

# ============================================================================
# STEP 3: Import Predictions and Evaluate
# ============================================================================

Write-Step "STEP 3: Importing Predictions and Evaluating"

$gitCommit = (git rev-parse --short HEAD 2>$null) -replace "`n", ""
if (-not $gitCommit) { $gitCommit = "unknown" }

foreach ($config in $configs) {
    if ($config.Skip) { continue }
    
    $predsCsv = "evidence/ablation/csv/preds_$($config.Name).csv"
    
    if (-not (Test-Path $predsCsv)) {
        Write-Error-Custom "Predictions CSV not found for $($config.Name): $predsCsv"
        continue
    }
    
    Write-Host "`n--- Importing $($config.Name) ---" -ForegroundColor Yellow
    
    $sourceNote = "Ablation-$($config.Name): $($config.Description); config=$ConfigPath; commit=$gitCommit; timestamp=$timestamp"
    
    $importArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "import-preds",
        "--csv", $predsCsv,
        "--source-note", $sourceNote
    )
    
    & python @importArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Import failed for $($config.Name)"
        continue
    }
    
    # Save import manifest
    if (Test-Path "reports/supa_benchmark_last_import_manifest.json") {
        Save-Evidence "reports/supa_benchmark_last_import_manifest.json" "evidence/ablation/metrics/$($config.Name)_import_manifest.json"
    }
    
    Write-Host "`n--- Evaluating $($config.Name) ---" -ForegroundColor Yellow
    
    $evalArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "eval"
    )
    
    & python @evalArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Eval failed for $($config.Name)"
        continue
    }
    
    # Save metrics
    if (Test-Path "reports/supa_benchmark_last_metrics.json") {
        Save-Evidence "reports/supa_benchmark_last_metrics.json" "evidence/ablation/metrics/$($config.Name)_metrics.json"
        Write-Success "Metrics saved for $($config.Name)"
    }
}

# ============================================================================
# STEP 4: Generate Summary
# ============================================================================

Write-Step "STEP 4: Generating Ablation Summary"

$summaryScript = "scripts/analysis/ablation_summary.py"

if (Test-Path $summaryScript) {
    & python $summaryScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Summary generated successfully"
        
        # Save summary evidence
        if (Test-Path "reports/ablation_summary_table.csv") {
            Save-Evidence "reports/ablation_summary_table.csv" "evidence/ablation/summary/ablation_summary.csv"
        }
        if (Test-Path "reports/ablation_summary_table.md") {
            Save-Evidence "reports/ablation_summary_table.md" "evidence/ablation/summary/ablation_summary.md"
        }
    } else {
        Write-Error-Custom "Summary generation failed"
    }
} else {
    Write-Host "Summary script not found. Run manually: python $summaryScript" -ForegroundColor Yellow
}

# ============================================================================
# FINAL REPORT
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Green
Write-Host "  ABLATION STUDY COMPLETED" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nRun ID: $RunId" -ForegroundColor White
Write-Host "Cohort Size: $N" -ForegroundColor White
Write-Host "Seed: $Seed" -ForegroundColor White
Write-Host "Noise Profile: $NoiseProfile" -ForegroundColor White
Write-Host "`nEvidence Location: evidence/ablation/" -ForegroundColor Cyan
Write-Host "  - CSV files: evidence/ablation/csv/" -ForegroundColor White
Write-Host "  - Metrics: evidence/ablation/metrics/" -ForegroundColor White
Write-Host "  - Logs: evidence/ablation/logs/" -ForegroundColor White
Write-Host "  - Summary: evidence/ablation/summary/" -ForegroundColor White
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Review summary: evidence/ablation/summary/ablation_summary.md" -ForegroundColor White
Write-Host "  2. Check checklist: evidence/ablation/CHECKLIST.md" -ForegroundColor White
Write-Host "  3. Proceed to Stratified K=5 if results are satisfactory" -ForegroundColor White
Write-Host "`n"
