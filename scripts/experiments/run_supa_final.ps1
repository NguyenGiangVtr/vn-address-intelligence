# ============================================================================
# SUPA-BENCH FINAL - Automated Wrapper Script
# ============================================================================
# Mục tiêu: Báo cáo chính thức với N=10,000, nhiễu SUP-D2-1.0.0 (high noise)
#
# Đây là thực nghiệm cuối cùng, sử dụng:
#   - Cohort lớn: N=10,000
#   - Nhiễu nặng: SUP-D2-1.0.0 (không dấu, viết tắt 90%, lỗi nặng)
#   - Cấu hình tốt nhất từ Ablation Study
#   - Seed cố định cho tái lập: 42
#
# Usage:
#   .\scripts\experiments\run_supa_final.ps1
#   .\scripts\experiments\run_supa_final.ps1 -N 10000 -Seed 42
#   .\scripts\experiments\run_supa_final.ps1 -SkipExtract -RunId 100
# ============================================================================

param(
    [int] $N = 10000,
    [int] $Seed = 42,
    [string] $NoiseProfile = "SUP-D2-1.0.0",
    [string] $ConfigPath = "app/ai/config.yaml",
    [string] $BestConfig = "A1",  # From Ablation results
    [int] $BatchSize = 100,  # For large cohort processing
    [switch] $SkipExtract,
    [int] $RunId = 0,
    [switch] $SkipPipeline,
    [switch] $SkipImport,
    [switch] $SkipEval,
    [switch] $SkipLatex
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
# STEP 1: Extract Large Cohort with High Noise
# ============================================================================

if (-not $SkipExtract) {
    Write-Step "STEP 1: Extracting SUPA-Bench Final Cohort (N=$N, Seed=$Seed, Noise=$NoiseProfile)"
    
    Write-Host "WARNING: This will create a large cohort with HIGH NOISE profile" -ForegroundColor Yellow
    Write-Host "  - N = $N specimens" -ForegroundColor Yellow
    Write-Host "  - Noise = $NoiseProfile (no diacritics, 90% abbreviation, heavy typos)" -ForegroundColor Yellow
    Write-Host "  - Seed = $Seed (for reproducibility)" -ForegroundColor Yellow
    Write-Host "`nThis may take several minutes..." -ForegroundColor Yellow
    
    $extractArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "extract",
        "--n", "$N",
        "--seed", "$Seed",
        "--noise-profile", $NoiseProfile,
        "--notes", "SUPA-Bench Final - High Noise D2 - Official Report"
    )
    
    Write-Host "`n>>> python $($extractArgs -join ' ')" -ForegroundColor Yellow
    & python @extractArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Extract failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    
    # Get run_id
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
    $specimensCsv = "reports/supa_final_specimens_d2.csv"
    $exportArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "export-specimens",
        "--out", $specimensCsv
    )
    & python @exportArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Export specimens failed"
        exit $LASTEXITCODE
    }
    
    # Verify specimen count
    if (Test-Path $specimensCsv) {
        $lineCount = (Get-Content $specimensCsv | Measure-Object -Line).Lines - 1
        Write-Success "Exported $lineCount specimens"
        
        if ($lineCount -ne $N) {
            Write-Host "WARNING: Expected $N specimens but got $lineCount" -ForegroundColor Yellow
        }
    }
    
    # Save evidence
    Save-Evidence $specimensCsv "evidence/final/cohort/specimens.csv"
    Save-Evidence $runIdFile "evidence/final/cohort/run_id.txt"
    
    # Sample 10 rows for quality check
    Write-Host "`nSampling 10 rows for quality check..." -ForegroundColor Yellow
    $sampleRows = Get-Content $specimensCsv | Select-Object -First 11 | Out-String
    $sampleRows | Out-File "evidence/final/cohort/sample_10_rows.txt" -Encoding UTF8
    Write-Success "Sample saved to evidence/final/cohort/sample_10_rows.txt"
    
    Write-Success "STEP 1 completed. Cohort ready for processing."
} else {
    Write-Step "STEP 1: Skipped (using existing Run ID: $RunId)"
    if ($RunId -eq 0) {
        Write-Error-Custom "Must provide -RunId when using -SkipExtract"
        exit 1
    }
}

# ============================================================================
# STEP 2: Run Pipeline (with batching for large cohort)
# ============================================================================

if (-not $SkipPipeline) {
    Write-Step "STEP 2: Running Pipeline for N=$N specimens (Config: $BestConfig)"
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $gitCommit = (git rev-parse --short HEAD 2>$null) -replace "`n", ""
    if (-not $gitCommit) { $gitCommit = "unknown" }
    
    # Determine pipeline args based on best config
    $pipelineBaseArgs = @(
        "src/app/ai/production_pipeline.py",
        "--config", $ConfigPath,
        "--supa-run-id", "$RunId",
        "--limit", "$N"
    )
    
    switch ($BestConfig) {
        "A1" { $configArgs = @() }  # Full
        "A2" { $configArgs = @("--no-llm") }
        "A3" { $configArgs = @("--no-ner", "--no-llm", "--retriever-type", "mgte") }
        "A4" { $configArgs = @("--no-retrieval") }
        "A5" { $configArgs = @("--retriever-type", "phobert") }
        default {
            Write-Error-Custom "Unknown config: $BestConfig"
            exit 1
        }
    }
    
    $outputCsv = "reports/supa_final_preds_d2.csv"
    $logFile = "evidence/final/predictions/pipeline_$timestamp.log"
    
    $pipelineArgs = $pipelineBaseArgs + @("--output-csv", $outputCsv) + $configArgs
    
    Write-Host ">>> python $($pipelineArgs -join ' ')" -ForegroundColor Yellow
    Write-Host "`nNote: Processing $N specimens may take 30-60 minutes depending on GPU" -ForegroundColor Yellow
    Write-Host "Progress will be logged to: $logFile" -ForegroundColor Yellow
    
    # Run pipeline and capture output
    $startTime = Get-Date
    $output = & python @pipelineArgs 2>&1 | Tee-Object -FilePath $logFile
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalMinutes
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Pipeline failed with exit code $LASTEXITCODE"
        Write-Host "Check log: $logFile" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    
    # Verify output
    if (Test-Path $outputCsv) {
        $lineCount = (Get-Content $outputCsv | Measure-Object -Line).Lines - 1
        Write-Success "Pipeline completed in $([math]::Round($duration, 2)) minutes"
        Write-Success "Output: $lineCount rows"
        
        if ($lineCount -ne $N) {
            Write-Host "WARNING: Expected $N predictions but got $lineCount" -ForegroundColor Yellow
        }
        
        # Save predictions evidence
        Save-Evidence $outputCsv "evidence/final/predictions/preds.csv"
    } else {
        Write-Error-Custom "Output CSV not found"
        exit 1
    }
    
    Write-Success "STEP 2 completed. Predictions ready for import."
} else {
    Write-Step "STEP 2: Skipped (using existing predictions)"
}

# ============================================================================
# STEP 3: Import Predictions
# ============================================================================

if (-not $SkipImport) {
    Write-Step "STEP 3: Importing Predictions"
    
    $predsCsv = "evidence/final/predictions/preds.csv"
    
    if (-not (Test-Path $predsCsv)) {
        Write-Error-Custom "Predictions CSV not found: $predsCsv"
        exit 1
    }
    
    $gitCommit = (git rev-parse --short HEAD 2>$null) -replace "`n", ""
    if (-not $gitCommit) { $gitCommit = "unknown" }
    
    $sourceNote = "SUPA-Bench-Final: N=$N; Config=$BestConfig; Noise=$NoiseProfile; Seed=$Seed; config=$ConfigPath; commit=$gitCommit"
    
    $importArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "import-preds",
        "--csv", $predsCsv,
        "--source-note", $sourceNote
    )
    
    Write-Host ">>> python $($importArgs -join ' ')" -ForegroundColor Yellow
    & python @importArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Import failed"
        exit $LASTEXITCODE
    }
    
    # Save import manifest
    if (Test-Path "reports/supa_benchmark_last_import_manifest.json") {
        Save-Evidence "reports/supa_benchmark_last_import_manifest.json" "evidence/final/report/import_manifest.json"
        Write-Success "Import manifest saved"
    }
    
    Write-Success "STEP 3 completed. Predictions imported to database."
} else {
    Write-Step "STEP 3: Skipped"
}

# ============================================================================
# STEP 4: Evaluate
# ============================================================================

if (-not $SkipEval) {
    Write-Step "STEP 4: Evaluating Results"
    
    $evalArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "eval"
    )
    
    Write-Host ">>> python $($evalArgs -join ' ')" -ForegroundColor Yellow
    & python @evalArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Eval failed"
        exit $LASTEXITCODE
    }
    
    # Save metrics
    if (Test-Path "reports/supa_benchmark_last_metrics.json") {
        $metricsFile = "reports/supa_final_metrics_d2_n10000.json"
        Copy-Item "reports/supa_benchmark_last_metrics.json" $metricsFile -Force
        Save-Evidence $metricsFile "evidence/final/report/metrics.json"
        
        # Display key metrics
        $metrics = Get-Content $metricsFile | ConvertFrom-Json
        Write-Host "`n" -NoNewline
        Write-Host "KEY METRICS:" -ForegroundColor Cyan
        Write-Host "  EM@v2: $($metrics.em_v2_pct)%" -ForegroundColor White
        Write-Host "  EM@v1: $($metrics.em_v1_pct)%" -ForegroundColor White
        Write-Host "  N Scored: $($metrics.n_scored)" -ForegroundColor White
        
        if ($metrics.mean_latency_ms) {
            Write-Host "  Mean Latency: $($metrics.mean_latency_ms) ms" -ForegroundColor White
        }
        if ($metrics.p95_latency_ms) {
            Write-Host "  P95 Latency: $($metrics.p95_latency_ms) ms" -ForegroundColor White
        }
        if ($metrics.throughput_addr_per_sec) {
            Write-Host "  Throughput: $($metrics.throughput_addr_per_sec) addr/s" -ForegroundColor White
        }
        
        Write-Success "Metrics saved"
    }
    
    Write-Success "STEP 4 completed. Evaluation finished."
} else {
    Write-Step "STEP 4: Skipped"
}

# ============================================================================
# STEP 5: Export LaTeX Macros and Compile PDF
# ============================================================================

if (-not $SkipLatex) {
    Write-Step "STEP 5: Exporting LaTeX Macros and Compiling PDF"
    
    # Export TeX macros
    Write-Host "Exporting LaTeX macros..." -ForegroundColor Yellow
    $exportTexArgs = @(
        "scripts/experiments/supa_benchmark.py",
        "export-tex"
    )
    
    & python @exportTexArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Export-tex failed"
    } else {
        Write-Success "LaTeX macros exported to docs/scientific-report/vnai-supa-generated-metrics.tex"
        
        # Save evidence
        $texFile = "docs/scientific-report/vnai-supa-generated-metrics.tex"
        if (Test-Path $texFile) {
            Save-Evidence $texFile "evidence/final/report/vnai-supa-generated-metrics.tex"
        }
    }
    
    # Compile PDF
    Write-Host "`nCompiling PDF..." -ForegroundColor Yellow
    $pdfDir = "docs/scientific-report"
    
    if (Test-Path "$pdfDir/vnai-chapters-master.tex") {
        Push-Location $pdfDir
        
        Write-Host "Running xelatex (first pass)..." -ForegroundColor Yellow
        & xelatex vnai-chapters-master.tex 2>&1 | Out-Null
        
        Write-Host "Running xelatex (second pass for references)..." -ForegroundColor Yellow
        & xelatex vnai-chapters-master.tex 2>&1 | Out-Null
        
        Pop-Location
        
        if (Test-Path "$pdfDir/vnai-chapters-master.pdf") {
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $pdfBackup = "evidence/final/report/vnai-chapters-master_$timestamp.pdf"
            Copy-Item "$pdfDir/vnai-chapters-master.pdf" $pdfBackup -Force
            Write-Success "PDF compiled successfully"
            Write-Success "PDF backup saved to: $pdfBackup"
        } else {
            Write-Error-Custom "PDF compilation failed"
        }
    } else {
        Write-Host "LaTeX source not found, skipping PDF compilation" -ForegroundColor Yellow
    }
    
    Write-Success "STEP 5 completed."
} else {
    Write-Step "STEP 5: Skipped"
}

# ============================================================================
# FINAL REPORT
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SUPA-BENCH FINAL COMPLETED" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nRun ID: $RunId" -ForegroundColor White
Write-Host "Cohort Size: $N" -ForegroundColor White
Write-Host "Seed: $Seed" -ForegroundColor White
Write-Host "Noise Profile: $NoiseProfile (HIGH NOISE)" -ForegroundColor White
Write-Host "Best Config: $BestConfig" -ForegroundColor White
Write-Host "`nEvidence Location: evidence/final/" -ForegroundColor Cyan
Write-Host "  - Cohort: evidence/final/cohort/" -ForegroundColor White
Write-Host "  - Predictions: evidence/final/predictions/" -ForegroundColor White
Write-Host "  - Report: evidence/final/report/" -ForegroundColor White
Write-Host "`nKey Files:" -ForegroundColor Yellow
Write-Host "  - Metrics: evidence/final/report/metrics.json" -ForegroundColor White
Write-Host "  - LaTeX: evidence/final/report/vnai-supa-generated-metrics.tex" -ForegroundColor White
Write-Host "  - PDF: evidence/final/report/vnai-chapters-master_*.pdf" -ForegroundColor White
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Review metrics: evidence/final/report/metrics.json" -ForegroundColor White
Write-Host "  2. Check PDF: evidence/final/report/vnai-chapters-master_*.pdf" -ForegroundColor White
Write-Host "  3. Complete checklist: evidence/final/CHECKLIST.md" -ForegroundColor White
Write-Host "  4. Run validation: python scripts/analysis/validate_evidence.py" -ForegroundColor White
Write-Host "  5. Create final backup of all evidence/" -ForegroundColor White
Write-Host "`n"
Write-Host "============================================" -ForegroundColor Green
Write-Host "  ALL EXPERIMENTS COMPLETED!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`n"
