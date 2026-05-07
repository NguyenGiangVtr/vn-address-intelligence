# Phase 4.3 — Full queue cleanse (up to 500k PENDING rows).
# Prerequisites: .env with DB_*, models in app/ai/config.yaml, optional NER_MODEL_ID.
# Monitor: pipeline logs every 50 rows; periodic reports under reports/.
# If a previous pipeline is stuck on old corpus_limit, stop it first, then rerun with current config.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot)
$env:PYTHONPATH = "."
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

Write-Host "Starting production_pipeline --limit 500000 ..."
python app/ai/production_pipeline.py --config app/ai/config.yaml --limit 500000

Write-Host "Generating 24h summary JSON..."
python scripts/diagnostics/full_cleanse_summary.py --window-hours 24
