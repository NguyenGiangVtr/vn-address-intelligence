#!/usr/bin/env python3
"""
Evidence Validation Script
===========================
Kiểm tra tính đầy đủ và hợp lệ của bằng chứng cho cả 3 giai đoạn thực nghiệm.

Usage:
    python scripts/analysis/validate_evidence.py
    python scripts/analysis/validate_evidence.py --stage ablation
    python scripts/analysis/validate_evidence.py --stage stratified
    python scripts/analysis/validate_evidence.py --stage final
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EVIDENCE_DIR = ROOT / 'evidence'


class ValidationResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, check: str):
        self.passed.append(check)
    
    def add_fail(self, check: str, reason: str):
        self.failed.append(f"{check}: {reason}")
    
    def add_warning(self, check: str, reason: str):
        self.warnings.append(f"{check}: {reason}")
    
    def is_valid(self) -> bool:
        return len(self.failed) == 0
    
    def summary(self) -> str:
        total = len(self.passed) + len(self.failed) + len(self.warnings)
        return f"Passed: {len(self.passed)}/{total}, Failed: {len(self.failed)}, Warnings: {len(self.warnings)}"


def check_file_exists(filepath: Path, result: ValidationResult, check_name: str):
    """Check if a file exists."""
    if filepath.exists():
        result.add_pass(f"{check_name}: {filepath.name}")
    else:
        result.add_fail(check_name, f"File not found: {filepath}")


def check_json_valid(filepath: Path, result: ValidationResult, check_name: str) -> Optional[Dict]:
    """Check if JSON file is valid and return data."""
    if not filepath.exists():
        result.add_fail(check_name, f"File not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result.add_pass(f"{check_name}: Valid JSON")
        return data
    except Exception as e:
        result.add_fail(check_name, f"Invalid JSON: {e}")
        return None


def check_csv_line_count(filepath: Path, expected: int, result: ValidationResult, check_name: str):
    """Check if CSV has expected number of lines (excluding header)."""
    if not filepath.exists():
        result.add_fail(check_name, f"File not found: {filepath}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        actual = len(lines) - 1  # Exclude header
        if actual == expected:
            result.add_pass(f"{check_name}: {actual} rows")
        else:
            result.add_fail(check_name, f"Expected {expected} rows, got {actual}")
    except Exception as e:
        result.add_fail(check_name, f"Error reading CSV: {e}")


def check_metric_range(value: Optional[float], min_val: float, max_val: float, 
                       result: ValidationResult, check_name: str):
    """Check if metric is within valid range."""
    if value is None:
        result.add_warning(check_name, "Metric is None")
        return
    
    if min_val <= value <= max_val:
        result.add_pass(f"{check_name}: {value:.2f}")
    else:
        result.add_fail(check_name, f"Value {value:.2f} out of range [{min_val}, {max_val}]")


def validate_ablation(result: ValidationResult) -> bool:
    """Validate Ablation Study evidence."""
    print("\n" + "="*80)
    print("VALIDATING ABLATION STUDY")
    print("="*80)
    
    ablation_dir = EVIDENCE_DIR / 'ablation'
    
    # Check directory structure
    check_file_exists(ablation_dir / 'CHECKLIST.md', result, "Ablation checklist")
    check_file_exists(ablation_dir / 'run_id.txt', result, "Ablation run_id")
    
    # Check CSV files
    csv_dir = ablation_dir / 'csv'
    check_file_exists(csv_dir / 'specimens.csv', result, "Ablation specimens")
    check_csv_line_count(csv_dir / 'specimens.csv', 1000, result, "Ablation specimens count")
    
    for config in ['A1', 'A2', 'A3', 'A4', 'A5']:
        preds_file = csv_dir / f'preds_{config}.csv'
        check_file_exists(preds_file, result, f"Ablation {config} predictions")
        check_csv_line_count(preds_file, 1000, result, f"Ablation {config} count")
    
    # Check metrics
    metrics_dir = ablation_dir / 'metrics'
    for config in ['A1', 'A2', 'A3', 'A4', 'A5']:
        metrics_file = metrics_dir / f'{config}_metrics.json'
        data = check_json_valid(metrics_file, result, f"Ablation {config} metrics")
        
        if data:
            # Check n_scored
            n_scored = data.get('n_scored')
            if n_scored == 1000:
                result.add_pass(f"Ablation {config} n_scored: {n_scored}")
            else:
                result.add_fail(f"Ablation {config} n_scored", f"Expected 1000, got {n_scored}")
            
            # Check EM@v2 range
            em_v2 = data.get('em_v2_pct')
            check_metric_range(em_v2, 0, 100, result, f"Ablation {config} EM@v2")
    
    # Check summary
    summary_dir = ablation_dir / 'summary'
    check_file_exists(summary_dir / 'ablation_summary.csv', result, "Ablation summary CSV")
    check_file_exists(summary_dir / 'ablation_summary.md', result, "Ablation summary MD")
    
    # Check logs
    logs_dir = ablation_dir / 'logs'
    if logs_dir.exists():
        log_files = list(logs_dir.glob('*.log'))
        if len(log_files) >= 5:
            result.add_pass(f"Ablation logs: {len(log_files)} files")
        else:
            result.add_warning("Ablation logs", f"Expected 5+ log files, found {len(log_files)}")
    else:
        result.add_warning("Ablation logs", "Logs directory not found")
    
    return result.is_valid()


def validate_stratified(result: ValidationResult) -> bool:
    """Validate Stratified K=5 evidence."""
    print("\n" + "="*80)
    print("VALIDATING STRATIFIED K=5")
    print("="*80)
    
    stratified_dir = EVIDENCE_DIR / 'stratified'
    
    # Check directory structure
    check_file_exists(stratified_dir / 'CHECKLIST.md', result, "Stratified checklist")
    
    # Check runs
    runs_dir = stratified_dir / 'runs'
    check_file_exists(runs_dir / 'batch_range.json', result, "Stratified batch_range")
    
    batch_data = check_json_valid(runs_dir / 'batch_range.json', result, "Stratified batch_range JSON")
    
    if batch_data:
        min_run = batch_data.get('min_run_id')
        max_run = batch_data.get('max_run_id')
        
        if min_run and max_run:
            k_runs = max_run - min_run + 1
            if k_runs == 5:
                result.add_pass(f"Stratified K runs: {k_runs}")
            else:
                result.add_fail("Stratified K runs", f"Expected 5, got {k_runs}")
            
            # Check each run
            for run_id in range(min_run, max_run + 1):
                check_file_exists(runs_dir / f'specimens_run{run_id}.csv', result, f"Stratified run{run_id} specimens")
                check_file_exists(runs_dir / f'preds_run{run_id}.csv', result, f"Stratified run{run_id} preds")
                
                metrics_file = runs_dir / f'metrics_run{run_id}.json'
                data = check_json_valid(metrics_file, result, f"Stratified run{run_id} metrics")
                
                if data:
                    n_scored = data.get('n_scored')
                    if n_scored == 2000:
                        result.add_pass(f"Stratified run{run_id} n_scored: {n_scored}")
                    else:
                        result.add_fail(f"Stratified run{run_id} n_scored", f"Expected 2000, got {n_scored}")
    
    # Check aggregate
    comparison_dir = stratified_dir / 'comparison'
    aggregate_file = comparison_dir / 'aggregate_real.json'
    data = check_json_valid(aggregate_file, result, "Stratified aggregate")
    
    if data and 'rollup' in data:
        rollup = data['rollup']
        em_v2_mean = rollup.get('em_v2_pct', {}).get('mean')
        check_metric_range(em_v2_mean, 0, 100, result, "Stratified EM@v2 mean")
    
    # Check comparison
    check_file_exists(comparison_dir / 'oracle_vs_real.md', result, "Stratified comparison MD")
    check_file_exists(comparison_dir / 'oracle_vs_real.json', result, "Stratified comparison JSON")
    
    return result.is_valid()


def validate_final(result: ValidationResult) -> bool:
    """Validate SUPA-Bench Final evidence."""
    print("\n" + "="*80)
    print("VALIDATING SUPA-BENCH FINAL")
    print("="*80)
    
    final_dir = EVIDENCE_DIR / 'final'
    
    # Check directory structure
    check_file_exists(final_dir / 'CHECKLIST.md', result, "Final checklist")
    
    # Check cohort
    cohort_dir = final_dir / 'cohort'
    check_file_exists(cohort_dir / 'run_id.txt', result, "Final run_id")
    check_file_exists(cohort_dir / 'specimens.csv', result, "Final specimens")
    check_csv_line_count(cohort_dir / 'specimens.csv', 10000, result, "Final specimens count")
    check_file_exists(cohort_dir / 'sample_10_rows.txt', result, "Final sample")
    
    # Check predictions
    predictions_dir = final_dir / 'predictions'
    check_file_exists(predictions_dir / 'preds.csv', result, "Final predictions")
    check_csv_line_count(predictions_dir / 'preds.csv', 10000, result, "Final predictions count")
    
    # Check report
    report_dir = final_dir / 'report'
    metrics_file = report_dir / 'metrics.json'
    data = check_json_valid(metrics_file, result, "Final metrics")
    
    if data:
        # Check n_scored
        n_scored = data.get('n_scored')
        if n_scored == 10000:
            result.add_pass(f"Final n_scored: {n_scored}")
        else:
            result.add_fail("Final n_scored", f"Expected 10000, got {n_scored}")
        
        # Check EM@v2
        em_v2 = data.get('em_v2_pct')
        check_metric_range(em_v2, 0, 100, result, "Final EM@v2")
        
        # Check if meets threshold
        if em_v2 is not None:
            if em_v2 >= 85.0:
                result.add_pass(f"Final EM@v2 meets threshold (≥85%): {em_v2:.2f}%")
            else:
                result.add_warning("Final EM@v2 threshold", f"Below 85%: {em_v2:.2f}%")
        
        # Check latency
        mean_latency = data.get('mean_latency_ms')
        if mean_latency is not None:
            check_metric_range(mean_latency, 0, 1000, result, "Final mean latency")
    
    check_file_exists(report_dir / 'import_manifest.json', result, "Final import manifest")
    check_file_exists(report_dir / 'vnai-supa-generated-metrics.tex', result, "Final LaTeX macros")
    
    # Check PDF
    pdf_files = list(report_dir.glob('vnai-chapters-master_*.pdf'))
    if len(pdf_files) > 0:
        result.add_pass(f"Final PDF: {len(pdf_files)} file(s)")
    else:
        result.add_warning("Final PDF", "No PDF backup found in evidence/final/report/")
    
    return result.is_valid()


def main():
    parser = argparse.ArgumentParser(description="Validate evidence for all experimental stages")
    parser.add_argument(
        '--stage',
        choices=['ablation', 'stratified', 'final', 'all'],
        default='all',
        help='Which stage to validate'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("EVIDENCE VALIDATION TOOL")
    print("=" * 80)
    print(f"\nEvidence directory: {EVIDENCE_DIR}")
    print(f"Validating stage: {args.stage}\n")
    
    result = ValidationResult()
    all_valid = True
    
    if args.stage in ['ablation', 'all']:
        if not validate_ablation(result):
            all_valid = False
    
    if args.stage in ['stratified', 'all']:
        if not validate_stratified(result):
            all_valid = False
    
    if args.stage in ['final', 'all']:
        if not validate_final(result):
            all_valid = False
    
    # Print summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"\n{result.summary()}\n")
    
    if result.passed:
        print(f"✓ PASSED ({len(result.passed)}):")
        for check in result.passed[:10]:  # Show first 10
            print(f"  - {check}")
        if len(result.passed) > 10:
            print(f"  ... and {len(result.passed) - 10} more")
    
    if result.warnings:
        print(f"\n⚠ WARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.failed:
        print(f"\n✗ FAILED ({len(result.failed)}):")
        for failure in result.failed:
            print(f"  - {failure}")
    
    print("\n" + "=" * 80)
    
    if all_valid and len(result.failed) == 0:
        print("✓ VALIDATION PASSED")
        print("=" * 80)
        print("\nAll evidence is valid and complete!")
        print("You can proceed with confidence.\n")
        return 0
    else:
        print("✗ VALIDATION FAILED")
        print("=" * 80)
        print("\nPlease fix the issues above before proceeding.")
        print("Check the checklists in evidence/*/CHECKLIST.md for guidance.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
