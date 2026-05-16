#!/usr/bin/env python3
"""
Compare Oracle vs Real Pipeline Results
========================================
So sánh kết quả giữa oracle baseline (run 56-60) và pipeline thật.

Usage:
    python scripts/analysis/compare_oracle_vs_real.py
    python scripts/analysis/compare_oracle_vs_real.py --oracle-json <path> --real-json <path>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def load_aggregate_json(filepath: Path) -> Optional[Dict]:
    """Load aggregate JSON file."""
    if not filepath.exists():
        print(f"[WARNING] File not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load {filepath}: {e}")
        return None


def extract_rollup_metrics(data: Dict) -> Dict:
    """Extract rollup metrics from aggregate JSON."""
    if not data or 'rollup' not in data:
        return {}
    
    rollup = data['rollup']
    
    return {
        'em_v2_mean': rollup.get('em_v2_pct', {}).get('mean'),
        'em_v2_std': rollup.get('em_v2_pct', {}).get('std'),
        'em_v2_min': rollup.get('em_v2_pct', {}).get('min'),
        'em_v2_max': rollup.get('em_v2_pct', {}).get('max'),
        'em_v1_mean': rollup.get('em_v1_pct', {}).get('mean'),
        'em_v1_std': rollup.get('em_v1_pct', {}).get('std'),
        'f1_duong_mean': rollup.get('f1_duong_pct', {}).get('mean'),
        'f1_phuong_mean': rollup.get('f1_phuong_pct', {}).get('mean'),
        'f1_quan_mean': rollup.get('f1_quan_pct', {}).get('mean'),
        'f1_tinh_mean': rollup.get('f1_tinh_pct', {}).get('mean'),
        'mean_latency': rollup.get('mean_latency_ms', {}).get('mean'),
        'p95_latency': rollup.get('p95_latency_ms', {}).get('mean'),
        'throughput': rollup.get('throughput_addr_per_sec', {}).get('mean')
    }


def format_value(value, is_percentage: bool = False, decimals: int = 2) -> str:
    """Format value for display."""
    if value is None:
        return "N/A"
    
    if is_percentage:
        return f"{value:.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}"


def calculate_gap(oracle_val, real_val) -> str:
    """Calculate gap between oracle and real."""
    if oracle_val is None or real_val is None:
        return "N/A"
    
    gap = oracle_val - real_val
    return f"{gap:+.2f}%"


def main():
    parser = argparse.ArgumentParser(description="Compare Oracle vs Real pipeline results")
    parser.add_argument(
        '--oracle-json',
        type=Path,
        default=ROOT / 'reports' / 'supa_benchmark_aggregate_stratified_k5_oracle_run56-60_20260513.json',
        help='Oracle aggregate JSON file'
    )
    parser.add_argument(
        '--real-json',
        type=Path,
        default=ROOT / 'reports' / 'supa_stratified_k5_real_pipeline.json',
        help='Real pipeline aggregate JSON file'
    )
    parser.add_argument(
        '--output-md',
        type=Path,
        default=ROOT / 'reports' / 'oracle_vs_real_comparison.md',
        help='Output Markdown file'
    )
    parser.add_argument(
        '--output-json',
        type=Path,
        default=ROOT / 'reports' / 'oracle_vs_real_comparison.json',
        help='Output JSON file'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("ORACLE VS REAL PIPELINE COMPARISON")
    print("=" * 80)
    print(f"\nOracle JSON: {args.oracle_json}")
    print(f"Real JSON: {args.real_json}")
    print(f"Output Markdown: {args.output_md}")
    print(f"Output JSON: {args.output_json}\n")
    
    # Load data
    print("Loading oracle baseline...")
    oracle_data = load_aggregate_json(args.oracle_json)
    
    print("Loading real pipeline results...")
    real_data = load_aggregate_json(args.real_json)
    
    if not oracle_data:
        print("[ERROR] Failed to load oracle data")
        sys.exit(1)
    
    if not real_data:
        print("[ERROR] Failed to load real pipeline data")
        sys.exit(1)
    
    # Extract metrics
    oracle_metrics = extract_rollup_metrics(oracle_data)
    real_metrics = extract_rollup_metrics(real_data)
    
    # Create comparison table
    comparison_data = []
    
    metrics_to_compare = [
        ('EM@v2 Mean (%)', 'em_v2_mean', True),
        ('EM@v2 Std (%)', 'em_v2_std', True),
        ('EM@v1 Mean (%)', 'em_v1_mean', True),
        ('EM@v1 Std (%)', 'em_v1_std', True),
        ('F1 Đường Mean (%)', 'f1_duong_mean', True),
        ('F1 Phường Mean (%)', 'f1_phuong_mean', True),
        ('F1 Quận Mean (%)', 'f1_quan_mean', True),
        ('F1 Tỉnh Mean (%)', 'f1_tinh_mean', True),
        ('Mean Latency (ms)', 'mean_latency', False),
        ('P95 Latency (ms)', 'p95_latency', False),
        ('Throughput (addr/s)', 'throughput', False)
    ]
    
    for metric_name, metric_key, is_pct in metrics_to_compare:
        oracle_val = oracle_metrics.get(metric_key)
        real_val = real_metrics.get(metric_key)
        
        comparison_data.append({
            'Metric': metric_name,
            'Oracle': format_value(oracle_val, is_pct),
            'Real Pipeline': format_value(real_val, is_pct),
            'Gap': calculate_gap(oracle_val, real_val) if is_pct else 'N/A'
        })
    
    df = pd.DataFrame(comparison_data)
    
    # Generate Markdown report
    md_content = "# So Sánh Oracle vs Real Pipeline\n\n"
    md_content += "## Tổng quan\n\n"
    md_content += "Báo cáo này so sánh kết quả giữa:\n\n"
    md_content += f"- **Oracle Baseline**: Kịch bản oracle (pred = ref_v2) trên run 56-60\n"
    md_content += f"  - File: `{args.oracle_json.name}`\n"
    md_content += f"- **Real Pipeline**: Pipeline thật với cấu hình tốt nhất từ Ablation Study\n"
    md_content += f"  - File: `{args.real_json.name}`\n"
    md_content += "\n## Bảng So Sánh\n\n"
    md_content += df.to_markdown(index=False)
    md_content += "\n\n## Phân Tích\n\n"
    
    # Analysis
    oracle_em_v2 = oracle_metrics.get('em_v2_mean')
    real_em_v2 = real_metrics.get('em_v2_mean')
    
    if oracle_em_v2 is not None and real_em_v2 is not None:
        gap = oracle_em_v2 - real_em_v2
        md_content += f"### EM@v2 (Exact Match)\n\n"
        md_content += f"- **Oracle**: {oracle_em_v2:.2f}% (kịch bản lý tưởng)\n"
        md_content += f"- **Real Pipeline**: {real_em_v2:.2f}% (pipeline thật)\n"
        md_content += f"- **Gap**: {gap:+.2f}%\n\n"
        
        if gap > 0:
            md_content += f"Pipeline thật đạt **{real_em_v2:.2f}%** so với oracle **{oracle_em_v2:.2f}%**, "
            md_content += f"cho thấy còn khoảng cách **{gap:.2f}%** cần cải thiện.\n\n"
        else:
            md_content += f"Pipeline thật đạt kết quả tương đương hoặc tốt hơn oracle.\n\n"
    
    # F1 Component Analysis
    md_content += "### F1-Score Theo Cấp Hành Chính\n\n"
    
    for level, key in [('Đường', 'f1_duong_mean'), ('Phường', 'f1_phuong_mean'), 
                       ('Quận', 'f1_quan_mean'), ('Tỉnh', 'f1_tinh_mean')]:
        oracle_f1 = oracle_metrics.get(key)
        real_f1 = real_metrics.get(key)
        
        if oracle_f1 is not None and real_f1 is not None:
            md_content += f"- **{level}**: Oracle {oracle_f1:.2f}% vs Real {real_f1:.2f}% "
            md_content += f"(Gap: {oracle_f1 - real_f1:+.2f}%)\n"
    
    md_content += "\n### Hiệu Năng (Latency & Throughput)\n\n"
    
    mean_lat_real = real_metrics.get('mean_latency')
    p95_lat_real = real_metrics.get('p95_latency')
    throughput_real = real_metrics.get('throughput')
    
    if mean_lat_real is not None:
        md_content += f"- **Mean Latency**: {mean_lat_real:.2f} ms\n"
    if p95_lat_real is not None:
        md_content += f"- **P95 Latency**: {p95_lat_real:.2f} ms\n"
    if throughput_real is not None:
        md_content += f"- **Throughput**: {throughput_real:.2f} addr/s\n"
    
    md_content += "\n## Kết Luận\n\n"
    
    if real_em_v2 is not None:
        if real_em_v2 >= 85.0:
            md_content += f"✅ Pipeline thật đạt **{real_em_v2:.2f}%** EM@v2, vượt ngưỡng kỳ vọng 85%.\n\n"
        else:
            md_content += f"⚠️ Pipeline thật đạt **{real_em_v2:.2f}%** EM@v2, chưa đạt ngưỡng kỳ vọng 85%.\n\n"
    
    md_content += "### Khuyến Nghị\n\n"
    
    if gap is not None and gap > 15:
        md_content += "- Gap lớn hơn 15% cho thấy cần cải thiện:\n"
        md_content += "  - Tăng chất lượng dữ liệu huấn luyện NER\n"
        md_content += "  - Mở rộng corpus retrieval\n"
        md_content += "  - Fine-tune LLM trên domain cụ thể\n"
        md_content += "  - Kiểm tra và cải thiện epoch detector\n"
    elif gap is not None and gap > 5:
        md_content += "- Gap trong khoảng chấp nhận được (5-15%):\n"
        md_content += "  - Tiếp tục theo dõi và cải thiện dần\n"
        md_content += "  - Tập trung vào các stratum khó (D2, D3)\n"
    else:
        md_content += "- Kết quả tốt, có thể tiến hành SUPA-Bench Final\n"
    
    md_content += "\n---\n"
    md_content += f"\n*Báo cáo được tạo tự động bởi `compare_oracle_vs_real.py`*\n"
    
    # Save Markdown
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_md, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"[✓] Markdown saved: {args.output_md}")
    
    # Save JSON
    comparison_json = {
        'oracle': {
            'source': str(args.oracle_json),
            'metrics': oracle_metrics,
            'metadata': oracle_data.get('metadata', {})
        },
        'real': {
            'source': str(args.real_json),
            'metrics': real_metrics,
            'metadata': real_data.get('metadata', {})
        },
        'comparison': comparison_data,
        'analysis': {
            'em_v2_gap': gap if gap is not None else None,
            'recommendation': 'proceed' if (real_em_v2 or 0) >= 85.0 else 'improve'
        }
    }
    
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(comparison_json, f, indent=2, ensure_ascii=False)
    print(f"[✓] JSON saved: {args.output_json}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(df.to_string(index=False))
    print("\n" + "=" * 80)
    
    if real_em_v2 is not None:
        print(f"\n[✓] Real Pipeline EM@v2: {real_em_v2:.2f}%")
        if real_em_v2 >= 85.0:
            print(f"[✓] Meets expectation threshold (≥85%)")
        else:
            print(f"[⚠] Below expectation threshold (≥85%)")
    
    print("\n[✓] Comparison completed successfully!")
    print(f"\nNext steps:")
    print(f"  1. Review: {args.output_md}")
    print(f"  2. Check checklist: evidence/stratified/CHECKLIST.md")
    print(f"  3. Proceed to SUPA-Bench Final if results are satisfactory\n")


if __name__ == '__main__':
    main()
