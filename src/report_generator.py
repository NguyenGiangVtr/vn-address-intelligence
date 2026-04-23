"""
report_generator.py
===================
Sinh báo cáo HTML so sánh hiệu năng 3 mô hình và lưu CSV kết quả.
"""

import os
from datetime import datetime
from typing import Dict, List

import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# HTML template
# ──────────────────────────────────────────────────────────────────────────────
_HTML_HEAD = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Báo Cáo Thực Nghiệm Chuẩn Hóa Địa Chỉ</title>
<style>
  body  {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background:#f5f7fa; color:#333; }}
  h1   {{ color:#2c3e50; border-bottom:3px solid #3498db; padding-bottom:10px; }}
  h2   {{ color:#34495e; margin-top:40px; }}
  table{{ border-collapse:collapse; width:100%; margin:20px 0; background:#fff;
          box-shadow:0 2px 6px rgba(0,0,0,.1); border-radius:8px; overflow:hidden; }}
  th   {{ background:#3498db; color:#fff; padding:12px 16px; text-align:left; }}
  td   {{ padding:10px 16px; border-bottom:1px solid #ecf0f1; }}
  tr:hover td {{ background:#f0f8ff; }}
  .best {{ font-weight:bold; color:#27ae60; }}
  .badge{{ display:inline-block; padding:3px 10px; border-radius:12px;
           font-size:12px; font-weight:bold; }}
  .green{{ background:#d5f5e3; color:#1e8449; }}
  .blue {{ background:#d6eaf8; color:#1a5276; }}
  .orange{{background:#fef9e7; color:#b7770d; }}
  .meta {{ font-size:13px; color:#777; margin-bottom:30px; }}
  .section{{ background:#fff; border-radius:8px; padding:24px;
             box-shadow:0 2px 6px rgba(0,0,0,.08); margin-bottom:30px; }}
  .winner {{ background:#eafaf1; border-left:5px solid #27ae60;
             padding:16px 20px; border-radius:6px; margin-top:20px; }}
</style>
</head>
<body>
"""

_HTML_FOOT = "</body></html>"


# ──────────────────────────────────────────────────────────────────────────────
def _fmt(val, suffix="", pct=False):
    if val is None:
        return "N/A"
    if pct:
        return f"{val*100:.2f}%"
    if isinstance(val, float):
        return f"{val:.4f}{suffix}"
    return str(val)


def _metric_table(all_metrics: Dict[str, Dict]) -> str:
    """Bảng so sánh metrics — highlight ô tốt nhất."""
    rows_def = [
        ("n_samples",       "Số mẫu",              False, False),
        ("exact_match",     "Exact Match",          True,  True),
        ("fuzzy_match",     "Fuzzy Match (≥0.85)",  True,  True),
        ("lev_score_mean",  "Levenshtein Score",    False, True),
        ("phuong_acc",      "Phường Accuracy",      True,  True),
        ("quan_acc",        "Quận Accuracy",        True,  True),
        ("tinh_acc",        "Tỉnh/TP Accuracy",     True,  True),
        ("latency_mean_ms", "Latency Mean (ms)",    False, False),
        ("latency_p95_ms",  "Latency P95 (ms)",     False, False),
        ("throughput_qps",  "Throughput (qps)",     False, True),
    ]

    model_names = list(all_metrics.keys())
    header_cells = "".join(f"<th>{n}</th>" for n in model_names)
    html = f"<table><tr><th>Chỉ số</th>{header_cells}</tr>"

    for key, label, is_pct, higher_is_better in rows_def:
        vals = {m: all_metrics[m].get(key) for m in model_names}
        valid = {m: v for m, v in vals.items() if v is not None}
        if not valid:
            continue

        best_model = (max if higher_is_better else min)(valid, key=lambda m: valid[m])
        cells = ""
        for m in model_names:
            v = vals[m]
            txt = _fmt(v, pct=is_pct)
            cls = ' class="best"' if (v is not None and m == best_model) else ""
            cells += f"<td{cls}>{txt}</td>"

        html += f"<tr><td>{label}</td>{cells}</tr>"

    html += "</table>"
    return html


def _winner_box(all_metrics: Dict[str, Dict]) -> str:
    """Xác định mô hình tốt nhất theo composite score."""
    weights = {
        "exact_match": 0.35,
        "fuzzy_match": 0.25,
        "phuong_acc":  0.15,
        "quan_acc":    0.15,
        "tinh_acc":    0.10,
    }
    scores = {}
    for model, m in all_metrics.items():
        scores[model] = sum(
            m.get(k, 0) * w for k, w in weights.items()
        )
    winner = max(scores, key=lambda m: scores[m])
    rows = "".join(
        f"<tr><td>{m}</td><td>{s:.4f}</td></tr>"
        for m, s in sorted(scores.items(), key=lambda x: -x[1])
    )
    return f"""
<div class="winner">
  <strong>🏆 Mô hình tốt nhất: {winner}</strong>
  <p>Composite score (weighted accuracy): {scores[winner]:.4f}</p>
  <table style="width:auto;margin:0">
    <tr><th>Mô hình</th><th>Composite Score</th></tr>
    {rows}
  </table>
</div>"""


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def generate_html_report(
    all_metrics: Dict[str, Dict],
    detail_df: pd.DataFrame,
    output_path: str,
):
    """
    Parameters
    ----------
    all_metrics : {"PhoBERT": {...}, "mGTE": {...}, "LLM": {...}}
    detail_df   : DataFrame mỗi dòng là 1 sample, cols: raw_address,
                  phobert_result, mgte_result, llm_result, standard_address (opt)
    output_path : đường dẫn file HTML đầu ra
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    badge_colors = ["green", "blue", "orange"]

    badges = "".join(
        f'<span class="badge {badge_colors[i % 3]}">{name}</span> '
        for i, name in enumerate(all_metrics)
    )

    metric_table_html = _metric_table(all_metrics)
    winner_html       = _winner_box(all_metrics)

    # Sample detail table (first 100 rows)
    sample_html = detail_df.head(100).to_html(
        index=False, border=0, classes="", escape=True
    )

    body = f"""
{_HTML_HEAD}
<h1>📊 Báo Cáo Thực Nghiệm — Chuẩn Hóa Địa Chỉ Việt Nam</h1>
<p class="meta">Ngày chạy: {now} &nbsp;|&nbsp; Mô hình: {badges}</p>

<div class="section">
  <h2>1. So sánh Chỉ số Đánh giá</h2>
  {metric_table_html}
  {winner_html}
</div>

<div class="section">
  <h2>2. Chi tiết Kết quả Mẫu (100 dòng đầu)</h2>
  {sample_html}
</div>
{_HTML_FOOT}
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"\n📄 Báo cáo HTML đã lưu: {output_path}")


def save_csv(detail_df: pd.DataFrame, csv_path: str):
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    detail_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"💾 CSV đã lưu: {csv_path}")
