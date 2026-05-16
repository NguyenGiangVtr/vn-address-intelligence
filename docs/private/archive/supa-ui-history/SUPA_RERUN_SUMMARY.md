# SUPA Benchmark Re-run Summary

**Date:** 2026-05-16  
**Git Commit:** 24a45cdd1ce9c27422b3158db35e3815614c854d  
**Status:** ✅ COMPLETED

## Overview

Successfully completed full SUPA benchmark re-run with upgraded noise function (`apply_noise`) following the runbook procedures documented in `docs/scientific-report/SUPA-BENCH-RUNBOOK.md`.

## Execution Summary

### 1. Data Cleanup ✅
- **Archived old data:** 91 files moved to `reports/archive_20260516_pre_upgrade/`
- **Database cleanup:** All old SUPA runs deleted from `prq.supa_benchmark_run` and `ath.supa_stratified_eval_summary`

### 2. Test Cohort (N=1000) ✅
- **Run ID:** 81
- **Seed:** 42 (fixed for reproducibility)
- **Noise Profile:** SUP-1.0.0 (standard)
- **Results:**
  - EM@v2: 100.0% (oracle demo)
  - EM@v1: 3.5%
  - F1 (all components): 100.0%
  - Mean latency: 5.11 ms
  - Throughput: 195.83 addr/s

### 3. Stratified K=5 Runs (N=2000 each) ✅
- **Run IDs:** 82-86
- **Base Seed:** 970156401
- **Seeds:** 970156401, 970157401, 970158401, 970159401, 970160401
- **Methodology:** strat-v1
- **Stratification:**
  - D1 (Urban Complex): ~42-45 samples (target 800, limited by data)
  - D2 (High Noise): ~1155-1158 samples (target 400, overflow due to D1 shortage)
  - D3 (Temporal/Lưỡng thời): 600 samples (30%)
  - D4 (GPS Boundary): 200 samples (10%)

**Note:** D1 and D2 quotas not met due to ground truth data constraints. PostGIS unavailable, D4 uses GPS-only proxy.

### 4. Aggregate Metrics (K=5) ✅

| Metric | Mean | Std Dev | Min | Max |
|--------|------|---------|-----|-----|
| **EM@v2** | 100.0% | 0.0% | 100.0% | 100.0% |
| **EM@v1** | 14.31% | 0.56% | 13.4% | 14.8% |
| **F1 Đường** | 100.0% | 0.0% | 100.0% | 100.0% |
| **F1 Phường** | 100.0% | 0.0% | 100.0% | 100.0% |
| **F1 Quận** | 100.0% | 0.0% | 100.0% | 100.0% |
| **F1 Tỉnh** | 100.0% | 0.0% | 100.0% | 100.0% |
| **Mean Latency** | 2.49 ms | 0.09 ms | 2.41 ms | 2.61 ms |
| **P95 Latency** | 2.80 ms | 0.12 ms | 2.67 ms | 3.01 ms |
| **Throughput** | 402.13 addr/s | 13.55 | 382.50 | 414.62 |

## Database Verification ✅

```
Total runs: 6 (1 test + 5 stratified)
Total specimens: 11,000 (1,000 + 10,000)
Stratified summaries: 1 (persisted in ath.supa_stratified_eval_summary)
```

## Artifacts Generated

### Reports
- `supa_benchmark_last_metrics.json` - Latest eval metrics (run 81)
- `supa_benchmark_aggregate_stratified_final.json` - K=5 aggregate
- `supa_benchmark_aggregate_stratified_final.md` - Human-readable summary
- `supa_benchmark_last_batch_range.json` - Batch metadata (runs 82-86)
- `supa_benchmark_last_import_manifest.json` - Import provenance
- `supa_metrics_run_{81-86}.json` - Individual run metrics
- `supa_workflow_specimens_latest.csv` - Latest specimens export
- `supa_benchmark_demo_preds_ref_v2.csv` - Oracle predictions

### LaTeX
- `docs/scientific-report/vnai-supa-generated-metrics.tex` - Updated macros

### Database
- `prq.supa_benchmark_run` - 6 runs with metadata
- `prq.supa_benchmark_specimen` - 11,000 specimens with predictions
- `ath.supa_stratified_eval_summary` - 1 aggregate record

## Important Notes

### ⚠️ Oracle Demo Mode
**All predictions used `--preds-demo-ref-v2` (oracle mode)** where `pred_standardized` was copied from `ref_address_v2`. This is:
- ✅ **Valid for:** Infrastructure testing, runbook verification, smoke testing
- ❌ **NOT valid for:** Scientific reporting, model evaluation, final paper numbers

**For scientific reporting:** Re-run with actual production pipeline predictions:
```powershell
python -m app.ai.production_pipeline --supa-run-id <RUN_ID> --limit <N>
python scripts/experiments/supa_benchmark.py import-preds --csv <PREDS.csv> --source-note "..."
```

### Noise Function Upgrade
The upgraded `apply_noise` function includes:
- **SUP-1.0.0:** Standard noise (65% abbreviation, basic IME errors, 40% prefix, 30% slang)
- **SUP-D2-1.0.0:** High noise (90% abbreviation, unaccented, heavy typos, 60% prefix/slang)

### Data Constraints
- **D1 shortage:** Only ~42-45 samples instead of target 800 (urban complex addresses limited in ground truth)
- **D2 overflow:** ~1155-1158 samples instead of target 400 (compensates for D1 shortage)
- **PostGIS unavailable:** D4 uses GPS-only proxy without boundary distance calculations

## Provenance

| Field | Value |
|-------|-------|
| **Git Commit** | 24a45cdd1ce9c27422b3158db35e3815614c854d |
| **Execution Date** | 2026-05-16 |
| **Python Version** | 3.11.9 |
| **Database** | 157.66.81.69:5432/vn_address_intelligence_db |
| **Noise Profiles** | SUP-1.0.0, STRATIFIED-strat-v1 |
| **Seeds** | 42 (test), 970156401-970160401 (stratified) |

## Next Steps for Scientific Reporting

1. **Run actual pipeline** on all 6 runs (81-86) with production models
2. **Import real predictions** with proper `--source-note` including:
   - Config file path
   - Model checkpoints (NER, mGTE, LLM)
   - Git commit
   - Hardware specs
3. **Re-run eval** to get true EM@v2, EM@v1, F1 scores
4. **Re-aggregate** with `--persist-ath` to update summary
5. **Export LaTeX** macros with real numbers
6. **Compile PDF** report

## Compliance Checklist

- ✅ Followed SUPA-BENCH-RUNBOOK.md procedures
- ✅ No modifications to `prq.ground_truth` (read-only)
- ✅ Proper seed management for reproducibility
- ✅ Provenance tracking (git commit, timestamps, source notes)
- ✅ Database integrity verified
- ✅ Artifacts archived before cleanup
- ⚠️ Oracle mode used (acceptable for infrastructure test, not for final report)
- ⚠️ D1/D2 quotas not met (data constraint, documented)
- ⚠️ PostGIS unavailable (D4 uses proxy, documented)

## Conclusion

The SUPA benchmark infrastructure has been successfully re-run with the upgraded noise function. All runbook procedures were followed correctly, and the system is ready for production pipeline evaluation. The oracle mode results (EM@v2=100%) confirm that the evaluation pipeline is working correctly. 

**For final scientific reporting, replace oracle predictions with actual model outputs.**
