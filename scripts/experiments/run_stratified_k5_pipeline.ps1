# ============================================================================
# STRATIFIED K=5 - Automated Wrapper Script
# ============================================================================
# Mục tiêu: Đo độ ổn định của cấu hình tốt nhất (từ Ablation) trên 5 cohort
# phân tầng độc lập với cơ cấu D1-D4
#
# Phân tầng:
#   D1 (40%): Chuẩn hóa đô thị phức tạp
#   D2 (20%): Nhiễu cao (không dấu, viết tắt 90%)
#   D3 (30%): Lưỡng thời và biến động hành chính
#   D4 (10%): Ranh giới không gian
#
# Usage:
#   .\scripts\experiments\run_stratified_k5_pipeline.ps1
#   .\scripts\experiments\run_stratified_k5_pipeline.ps1 -KRuns 5 -N 2000 -BaseSeed 970156401
#   .\scripts\experiments\run_stratified_k5_pipeline.ps1 -BestConfig A1 -SkipReplicate
# ============================================================================

param(
    [int] $KRuns = 5,
    [int] $N = 2000,
    [int] $BaseSeed = 970156401,
    [string] $StratVersion = "strat-v1",
    [string] $ConfigPath = "app/ai/config.yaml",
    [string] $BestConfig = "A1",  # From Ablation results
    [switch] $SkipReplicate,
    [string] $RunIdsRange = "",  # e.g., "61-65"
    [switch] $SkipPipeline,
    [switch] $SkipAggregate
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
# STEP 1: Run Replicate-Stratified (if not skipped)
# ============================================================================

if (-not $SkipReplicate) {
    Write-Step "STEP 1: Running Replicate-Stratified (K=$KRuns, N=$N per run)"
    
    $replicateArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "replicate-stratified",
        "--k-runs", "$KRuns",
        "--n", "$N",
        "--base-seed", "$BaseSeed",
        "--strat-version", $StratVersion,
        "--specimens-out", "reports/supa_workflow_specimens_latest.csv"
    )
    
    Write-Host ">>> python $($replicateArgs -join ' ')" -ForegroundColor Yellow
    Write-Host "Note: This will create $KRuns cohorts with stratified sampling (D1-D4)" -ForegroundColor Yellow
    Write-Host "Each cohort will have N=$N specimens" -ForegroundColor Yellow
    Write-Host "`nThis may take several minutes..." -ForegroundColor Yellow
    
    & python @replicateArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Replicate-stratified failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    
    # Get run IDs from batch range file
    $batchFile = "reports/supa_benchmark_last_batch_range.json"
    if (Test-Path $batchFile) {
        $batchData = Get-Content $batchFile | ConvertFrom-Json
        $minRunId = $batchData.min_run_id
        $maxRunId = $batchData.max_run_id
        $RunIdsRange = "$minRunId-$maxRunId"
        Write-Success "Replicate-stratified completed. Run IDs: $RunIdsRange"
        
        # Save evidence
        Save-Evidence $batchFile "evidence/stratified/runs/batch_range.json"
    } else {
        Write-Error-Custom "Could not find batch range file"
        exit 1
    }
    
    Write-Success "STEP 1 completed. Created $KRuns stratified cohorts."
} else {
    Write-Step "STEP 1: Skipped (using existing Run IDs: $RunIdsRange)"
    if (-not $RunIdsRange) {
        Write-Error-Custom "Must provide -RunIdsRange when using -SkipReplicate (e.g., '61-65')"
        exit 1
    }
}

# Parse run IDs range
$runIdParts = $RunIdsRange -split '-'
$minRunId = [int]$runIdParts[0]
$maxRunId = [int]$runIdParts[1]
$runIds = $minRunId..$maxRunId

Write-Host "`nProcessing Run IDs: $($runIds -join ', ')" -ForegroundColor Cyan

# ============================================================================
# STEP 2: Run Pipeline for Each Cohort
# ============================================================================

if (-not $SkipPipeline) {
    Write-Step "STEP 2: Running Pipeline for $KRuns Cohorts (Config: $BestConfig)"
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $gitCommit = (git rev-parse --short HEAD 2>$null) -replace "`n", ""
    if (-not $gitCommit) { $gitCommit = "unknown" }
    
    # Determine pipeline args based on best config
    $pipelineBaseArgs = @(
        "src/app/ai/production_pipeline.py",
        "--config", $ConfigPath,
        "--limit", "$N"
    )
    
    switch ($BestConfig) {
        "A1" { $configArgs = @() }  # Full
        "A2" { $configArgs = @("--no-llm") }  # No-LLM
        "A3" { $configArgs = @("--no-ner", "--no-llm", "--retriever-type", "mgte") }  # Retrieval-only
        "A4" { $configArgs = @("--no-retrieval") }  # NER + LLM
        "A5" { $configArgs = @("--retriever-type", "phobert") }  # PhoBERT Siamese
        default {
            Write-Error-Custom "Unknown config: $BestConfig"
            exit 1
        }
    }
    
    foreach ($runId in $runIds) {
        Write-Host "`n----------------------------------------" -ForegroundColor Cyan
        Write-Host "Processing Run ID: $runId" -ForegroundColor Cyan
        Write-Host "----------------------------------------" -ForegroundColor Cyan
        
        # Export specimens for this run
        Write-Host "Exporting specimens for run $runId..." -ForegroundColor Yellow
        $specimensCsv = "reports/stratified_specimens_run$runId.csv"
        $exportArgs = @(
            "scripts/experiments/supa_benchmark.py",
            "export-specimens",
            "--run-id", "$runId",
            "--out", $specimensCsv
        )
        & python @exportArgs
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Export specimens failed for run $runId"
            continue
        }
        
        # Save specimens evidence
        Save-Evidence $specimensCsv "evidence/stratified/runs/specimens_run$runId.csv"
        
        # Run pipeline
        Write-Host "Running pipeline for run $runId..." -ForegroundColor Yellow
        $outputCsv = "reports/stratified_preds_run${runId}_$timestamp.csv"
        $logFile = "evidence/stratified/runs/pipeline_run${runId}_$timestamp.log"
        
        $pipelineArgs = $pipelineBaseArgs + @("--supa-run-id", "$runId", "--output-csv", $outputCsv) + $configArgs
        
        Write-Host ">>> python $($pipelineArgs -join ' ')" -ForegroundColor Yellow
        
        # Run pipeline and capture output
        $output = & python @pipelineArgs 2>&1 | Tee-Object -FilePath $logFile
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Pipeline failed for run $runId"
            Write-Host "Check log: $logFile" -ForegroundColor Red
            continue
        }
        
        # Verify output
        if (Test-Path $outputCsv) {
            $lineCount = (Get-Content $outputCsv | Measure-Object -Line).Lines - 1
            Write-Success "Pipeline completed for run $runId. Output: $lineCount rows"
            
            # Save predictions evidence
            Save-Evidence $outputCsv "evidence/stratified/runs/preds_run$runId.csv"
        } else {
            Write-Error-Custom "Output CSV not found for run $runId"
            continue
        }
        
        # Import predictions
        Write-Host "Importing predictions for run $runId..." -ForegroundColor Yellow
        $sourceNote = "Stratified-K5-Run$runId: Config=$BestConfig; strat=$StratVersion; config=$ConfigPath; commit=$gitCommit; timestamp=$timestamp"
        
        $importArgs = @(
            "scripts/experiments/supa_benchmark.py",
            "import-preds",
            "--csv", "evidence/stratified/runs/preds_run$runId.csv",
            "--source-note", $sourceNote
        )
        
        & python @importArgs
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Import failed for run $runId"
            continue
        }
        
        # Save import manifest
        if (Test-Path "reports/supa_benchmark_last_import_manifest.json") {
            Save-Evidence "reports/supa_benchmark_last_import_manifest.json" "evidence/stratified/runs/import_manifest_run$runId.json"
        }
        
        # Evaluate
        Write-Host "Evaluating run $runId..." -ForegroundColor Yellow
        $evalArgs = @(
            "scripts/experiments/supa_benchmark.py",
            "eval"
        )
        
        & python @evalArgs
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Eval failed for run $runId"
            continue
        }
        
        # Save metrics
        if (Test-Path "reports/supa_benchmark_last_metrics.json") {
            Save-Evidence "reports/supa_benchmark_last_metrics.json" "evidence/stratified/runs/metrics_run$runId.json"
            Write-Success "Metrics saved for run $runId"
        }
    }
    
    Write-Success "STEP 2 completed. Processed $KRuns cohorts."
} else {
    Write-Step "STEP 2: Skipped (using existing predictions)"
}

# ============================================================================
# STEP 3: Aggregate Results
# ============================================================================

if (-not $SkipAggregate) {
    Write-Step "STEP 3: Aggregating Results from $KRuns Runs"
    
    $aggregateArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "aggregate-runs",
        "--from-batch-json", "evidence/stratified/runs/batch_range.json",
        "--persist-ath",
        "--methodology-version", $StratVersion,
        "--out-json", "reports/supa_stratified_k5_real_pipeline.json",
        "--out-md", "reports/supa_stratified_k5_real_pipeline.md"
    )
    
    Write-Host ">>> python $($aggregateArgs -join ' ')" -ForegroundColor Yellow
    
    & python @aggregateArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Aggregate failed"
        exit $LASTEXITCODE
    }
    
    # Save aggregate evidence
    if (Test-Path "reports/supa_stratified_k5_real_pipeline.json") {
        Save-Evidence "reports/supa_stratified_k5_real_pipeline.json" "evidence/stratified/comparison/aggregate_real.json"
        Write-Success "Aggregate JSON saved"
    }
    
    if (Test-Path "reports/supa_stratified_k5_real_pipeline.md") {
        Save-Evidence "reports/supa_stratified_k5_real_pipeline.md" "evidence/stratified/comparison/aggregate_real.md"
        Write-Success "Aggregate Markdown saved"
    }
    
    # Query ath table for evidence
    Write-Host "`nQuerying ath.supa_stratified_eval_summary..." -ForegroundColor Yellow
    $sqlQuery = "SELECT * FROM ath.supa_stratified_eval_summary ORDER BY id DESC LIMIT 1"
    Write-Host "SQL: $sqlQuery" -ForegroundColor Gray
    Write-Host "Note: Run this query manually and save screenshot to evidence/stratified/sql/" -ForegroundColor Yellow
    
    Write-Success "STEP 3 completed. Aggregate results saved."
} else {
    Write-Step "STEP 3: Skipped"
}

# ============================================================================
# STEP 4: Compare with Oracle Baseline
# ============================================================================

Write-Step "STEP 4: Comparing with Oracle Baseline"

$compareScript = "scripts/analysis/compare_oracle_vs_real.py"

if (Test-Path $compareScript) {
    & python $compareScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Comparison generated successfully"
        
        # Save comparison evidence
        if (Test-Path "reports/oracle_vs_real_comparison.md") {
            Save-Evidence "reports/oracle_vs_real_comparison.md" "evidence/stratified/comparison/oracle_vs_real.md"
        }
        if (Test-Path "reports/oracle_vs_real_comparison.json") {
            Save-Evidence "reports/oracle_vs_real_comparison.json" "evidence/stratified/comparison/oracle_vs_real.json"
        }
    } else {
        Write-Error-Custom "Comparison generation failed"
    }
} else {
    Write-Host "Comparison script not found. Run manually: python $compareScript" -ForegroundColor Yellow
}

# ============================================================================
# FINAL REPORT
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Green
Write-Host "  STRATIFIED K=5 COMPLETED" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nRun IDs: $RunIdsRange" -ForegroundColor White
Write-Host "K Runs: $KRuns" -ForegroundColor White
Write-Host "N per run: $N" -ForegroundColor White
Write-Host "Base Seed: $BaseSeed" -ForegroundColor White
Write-Host "Stratification: $StratVersion" -ForegroundColor White
Write-Host "Best Config: $BestConfig" -ForegroundColor White
Write-Host "`nEvidence Location: evidence/stratified/" -ForegroundColor Cyan
Write-Host "  - Run data: evidence/stratified/runs/" -ForegroundColor White
Write-Host "  - SQL dumps: evidence/stratified/sql/" -ForegroundColor White
Write-Host "  - Comparisons: evidence/stratified/comparison/" -ForegroundColor White
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Review aggregate: evidence/stratified/comparison/aggregate_real.md" -ForegroundColor White
Write-Host "  2. Review comparison: evidence/stratified/comparison/oracle_vs_real.md" -ForegroundColor White
Write-Host "  3. Check checklist: evidence/stratified/CHECKLIST.md" -ForegroundColor White
Write-Host "  4. Proceed to SUPA-Bench Final if results are satisfactory" -ForegroundColor White
Write-Host "`n"
