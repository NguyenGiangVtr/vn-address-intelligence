#!/usr/bin/env python3
"""
Ablation Study Summary Generator
=================================
Đọc metrics từ 5 cấu hình Ablation (A1-A5) và tạo bảng so sánh.

Usage:
    python scripts/analysis/ablation_summary.py
    python scripts/analysis/ablation_summary.py --metrics-dir evidence/ablation/metrics
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def load_metrics(config_name: str, metrics_dir: Path) -> Optional[Dict]:
    """Load metrics JSON for a specific configuration."""
    metrics_file = metrics_dir / f"{config_name}_metrics.json"
    
    if not metrics_file.exists():
        print(f"[WARNING] Metrics file not found: {metrics_file}")
        return None
    
    try:
        with open(metrics_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load {metrics_file}: {e}")
        return None


def extract_metrics(data: Dict) -> Dict:
    """Extract key metrics from JSON data."""
    if not data:
        return {
            'em_v2_pct': None,
            'em_v1_pct': None,
            'n_scored': None,
            'mean_latency_ms': None,
            'p95_latency_ms': None,
            'throughput_addr_per_sec': None,
            'f1_duong_pct': None,
            'f1_phuong_pct': None,
            'f1_quan_pct': None,
            'f1_tinh_pct': None
        }
    
    return {
        'em_v2_pct': data.get('em_v2_pct'),
        'em_v1_pct': data.get('em_v1_pct'),
        'n_scored': data.get('n_scored'),
        'mean_latency_ms': data.get('mean_latency_ms'),
        'p95_latency_ms': data.get('p95_latency_ms'),
        'throughput_addr_per_sec': data.get('throughput_addr_per_sec'),
        'f1_duong_pct': data.get('f1_duong_pct'),
        'f1_phuong_pct': data.get('f1_phuong_pct'),
        'f1_quan_pct': data.get('f1_quan_pct'),
        'f1_tinh_pct': data.get('f1_tinh_pct')
    }


def format_value(value, is_percentage: bool = False, decimals: int = 2) -> str:
    """Format value for display."""
    if value is None:
        return "N/A"
    
    if is_percentage:
        return f"{value:.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}"


def main():
    parser = argparse.ArgumentParser(description="Generate Ablation Study summary")
    parser.add_argument(
        '--metrics-dir',
        type=Path,
        default=ROOT / 'evidence' / 'ablation' / 'metrics',
        help='Directory containing metrics JSON files'
    )
    parser.add_argument(
        '--output-csv',
        type=Path,
        default=ROOT / 'reports' / 'ablation_summary_table.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--output-md',
        type=Path,
        default=ROOT / 'reports' / 'ablation_summary_table.md',
        help='Output Markdown file path'
    )
    parser.add_argument(
        '--output-json',
        type=Path,
        default=ROOT / 'evidence' / 'ablation' / 'summary' / 'ablation_comparison.json',
        help='Output JSON file path'
    )
    
    args = parser.parse_args()
    
    # Configuration definitions
    configs = [
        {'name': 'A1', 'description': 'Full (NER + mGTE + LLM)'},
        {'name': 'A2', 'description': 'No-LLM (NER + mGTE)'},
        {'name': 'A3', 'description': 'Retrieval-only (mGTE)'},
        {'name': 'A4', 'description': 'NER + LLM (no retrieval)'},
        {'name': 'A5', 'description': 'PhoBERT Siamese (NER + PhoBERT + LLM)'}
    ]
    
    print("=" * 80)
    print("ABLATION STUDY SUMMARY GENERATOR")
    print("=" * 80)
    print(f"\nMetrics directory: {args.metrics_dir}")
    print(f"Output CSV: {args.output_csv}")
    print(f"Output Markdown: {args.output_md}")
    print(f"Output JSON: {args.output_json}\n")
    
    # Load metrics for all configurations
    results = []
    all_data = {}
    
    for config in configs:
        name = config['name']
        desc = config['description']
        
        print(f"Loading metrics for {name}: {desc}...")
        data = load_metrics(name, args.metrics_dir)
        metrics = extract_metrics(data)
        
        results.append({
            'Config': name,
            'Description': desc,
            'EM@v2 (%)': metrics['em_v2_pct'],
            'EM@v1 (%)': metrics['em_v1_pct'],
            'N Scored': metrics['n_scored'],
            'Mean Latency (ms)': metrics['mean_latency_ms'],
            'P95 Latency (ms)': metrics['p95_latency_ms'],
            'Throughput (addr/s)': metrics['throughput_addr_per_sec'],
            'F1 Đường (%)': metrics['f1_duong_pct'],
            'F1 Phường (%)': metrics['f1_phuong_pct'],
            'F1 Quận (%)': metrics['f1_quan_pct'],
            'F1 Tỉnh (%)': metrics['f1_tinh_pct']
        })
        
        all_data[name] = {
            'description': desc,
            'metrics': metrics,
            'raw_data': data
        }
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save CSV
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output_csv, index=False, encoding='utf-8')
    print(f"\n[✓] CSV saved: {args.output_csv}")
    
    # Save Markdown
    md_content = "# Ablation Study - Bảng So Sánh Kết Quả\n\n"
    md_content += "## Tổng quan\n\n"
    md_content += "Bảng dưới đây so sánh hiệu năng của 5 cấu hình thực nghiệm Ablation Study:\n\n"
    
    for config in configs:
        md_content += f"- **{config['name']}**: {config['description']}\n"
    
    md_content += "\n## Kết quả chi tiết\n\n"
    md_content += df.to_markdown(index=False)
    md_content += "\n\n## Giải thích các chỉ số\n\n"
    md_content += "- **EM@v2**: Exact Match so với tham chiếu hậu cải cách (v2)\n"
    md_content += "- **EM@v1**: Exact Match so với tham chiếu tiền cải cách (v1)\n"
    md_content += "- **N Scored**: Số mẫu được đánh giá (có predictions)\n"
    md_content += "- **Mean Latency**: Thời gian xử lý trung bình mỗi địa chỉ (ms)\n"
    md_content += "- **P95 Latency**: Độ trễ tại phân vị 95% (ms)\n"
    md_content += "- **Throughput**: Số địa chỉ xử lý được mỗi giây\n"
    md_content += "- **F1 Đường/Phường/Quận/Tỉnh**: F1-Score cho từng cấp hành chính\n"
    md_content += "\n## Nhận xét\n\n"
    
    # Find best configuration
    valid_em = [(i, r['EM@v2 (%)']) for i, r in enumerate(results) if r['EM@v2 (%)'] is not None]
    if valid_em:
        best_idx, best_em = max(valid_em, key=lambda x: x[1])
        best_config = results[best_idx]
        md_content += f"- **Cấu hình tốt nhất**: {best_config['Config']} ({best_config['Description']}) "
        md_content += f"với EM@v2 = {best_config['EM@v2 (%)']}%\n"
    
    # Latency comparison
    valid_latency = [(i, r['Mean Latency (ms)']) for i, r in enumerate(results) if r['Mean Latency (ms)'] is not None]
    if valid_latency:
        fastest_idx, fastest_latency = min(valid_latency, key=lambda x: x[1])
        fastest_config = results[fastest_idx]
        md_content += f"- **Cấu hình nhanh nhất**: {fastest_config['Config']} ({fastest_config['Description']}) "
        md_content += f"với Mean Latency = {fastest_config['Mean Latency (ms)']} ms\n"
    
    md_content += "\n---\n"
    md_content += f"\n*Báo cáo được tạo tự động bởi `ablation_summary.py`*\n"
    
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_md, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"[✓] Markdown saved: {args.output_md}")
    
    # Save JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print(f"[✓] JSON saved: {args.output_json}")
    
    # Print summary to console
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(df.to_string(index=False))
    print("\n" + "=" * 80)
    
    if valid_em:
        print(f"\n[✓] Best configuration: {best_config['Config']} with EM@v2 = {best_config['EM@v2 (%)']}%")
    
    print("\n[✓] Ablation summary generation completed successfully!")
    print(f"\nNext steps:")
    print(f"  1. Review: {args.output_md}")
    print(f"  2. Check checklist: evidence/ablation/CHECKLIST.md")
    print(f"  3. Proceed to Stratified K=5 if results are satisfactory\n")


if __name__ == '__main__':
    main()
