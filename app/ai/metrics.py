"""
metrics.py
==========
Tập hợp các hàm đo lường chất lượng chuẩn hóa địa chỉ:
- Exact Match (EM)
- Levenshtein / Normalized Edit Distance
- Component Accuracy (Phường / Quận / Tỉnh)
- Latency statistics
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# String utils
# ──────────────────────────────────────────────────────────────────────────────
def _normalize_str(s: str) -> str:
    """Lowercase, strip diacritics, remove punctuation để so sánh."""
    s = s.lower().strip()
    # NFD decompose → remove combining marks
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def levenshtein_ratio(a: str, b: str) -> float:
    """Trả về tỷ lệ tương đồng Levenshtein trong [0, 1]."""
    return SequenceMatcher(None, a, b).ratio()


# ──────────────────────────────────────────────────────────────────────────────
# Vietnamese address component parser
# ──────────────────────────────────────────────────────────────────────────────
_PHUONG_PATTERN = re.compile(
    r"(ph[uư][oờ]ng|xa|th[iị] tr[aấ]n)\s+([^,]+)", re.IGNORECASE | re.UNICODE
)
_QUAN_PATTERN = re.compile(
    r"(qu[aậ]n|huy[eệ]n|th[àa]nh ph[oố]|t[pP]\.?)\s*([^,]+)", re.IGNORECASE | re.UNICODE
)
_TINH_PATTERN = re.compile(
    r"(t[iỉ]nh|th[àa]nh ph[oố])\s+([^,]+)$", re.IGNORECASE | re.UNICODE
)


def parse_components(address: str) -> Dict[str, str]:
    """Tách thô các thành phần hành chính."""
    parts = {"phuong": "", "quan": "", "tinh": ""}
    if not address:
        return parts
    m = _PHUONG_PATTERN.search(address)
    if m:
        parts["phuong"] = m.group(2).strip().rstrip(",")
    m = _QUAN_PATTERN.search(address)
    if m:
        parts["quan"] = m.group(2).strip().rstrip(",")
    m = _TINH_PATTERN.search(address)
    if m:
        parts["tinh"] = m.group(2).strip()
    return parts


# ──────────────────────────────────────────────────────────────────────────────
# Core metrics
# ──────────────────────────────────────────────────────────────────────────────
def compute_metrics(
    predictions: List[str],
    ground_truths: List[str],
    latencies_ms: Optional[List[float]] = None,
) -> Dict:
    """
    Tính đầy đủ các chỉ số cho một mô hình.

    Parameters
    ----------
    predictions   : kết quả chuẩn hóa của mô hình
    ground_truths : địa chỉ chuẩn (ground truth)
    latencies_ms  : thời gian xử lý mỗi query (ms)

    Returns
    -------
    dict với các key:
        exact_match, fuzzy_match, lev_score_mean,
        phuong_acc, quan_acc, tinh_acc,
        latency_mean_ms, latency_p95_ms, latency_p99_ms, throughput_qps
    """
    n = len(predictions)
    assert n == len(ground_truths), "predictions & ground_truths phải cùng độ dài"

    em_list, lev_list = [], []
    comp_hits = {"phuong": 0, "quan": 0, "tinh": 0}
    fuzzy_hits = 0

    for pred, gt in zip(predictions, ground_truths):
        pred_n = _normalize_str(pred or "")
        gt_n   = _normalize_str(gt or "")

        # Exact Match
        em = 1 if pred_n == gt_n else 0
        em_list.append(em)

        # Levenshtein
        lev = levenshtein_ratio(pred_n, gt_n)
        lev_list.append(lev)

        # Fuzzy (lev >= 0.85 coi là đúng)
        if lev >= 0.85:
            fuzzy_hits += 1

        # Component accuracy
        pred_c = parse_components(pred or "")
        gt_c   = parse_components(gt or "")
        for key in comp_hits:
            if _normalize_str(pred_c[key]) == _normalize_str(gt_c[key]) and gt_c[key]:
                comp_hits[key] += 1

    # Latency
    lat_stats: Dict = {}
    if latencies_ms:
        arr = np.array(latencies_ms)
        lat_stats = {
            "latency_mean_ms": float(np.mean(arr)),
            "latency_p95_ms":  float(np.percentile(arr, 95)),
            "latency_p99_ms":  float(np.percentile(arr, 99)),
            "throughput_qps":  float(1000.0 / np.mean(arr)) if np.mean(arr) > 0 else 0.0,
        }

    # Component denominators (only rows where GT has that component)
    def _denom(key):
        return sum(1 for _, gt in zip(predictions, ground_truths)
                   if parse_components(gt).get(key))

    results = {
        "n_samples":       n,
        "exact_match":     float(np.mean(em_list)),
        "fuzzy_match":     fuzzy_hits / n,
        "lev_score_mean":  float(np.mean(lev_list)),
        "phuong_acc":      comp_hits["phuong"] / max(_denom("phuong"), 1),
        "quan_acc":        comp_hits["quan"]   / max(_denom("quan"), 1),
        "tinh_acc":        comp_hits["tinh"]   / max(_denom("tinh"), 1),
        **lat_stats,
    }
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Pretty printer
# ──────────────────────────────────────────────────────────────────────────────
def print_metrics(model_name: str, metrics: Dict):
    pad = 35
    print(f"\n{'═'*60}")
    print(f"  📊  {model_name}")
    print(f"{'═'*60}")
    print(f"  {'Samples':<{pad}}: {metrics['n_samples']}")
    print(f"  {'Exact Match':<{pad}}: {metrics['exact_match']*100:.2f}%")
    print(f"  {'Fuzzy Match (≥0.85)':<{pad}}: {metrics['fuzzy_match']*100:.2f}%")
    print(f"  {'Levenshtein Score (mean)':<{pad}}: {metrics['lev_score_mean']:.4f}")
    print(f"  {'Phường Accuracy':<{pad}}: {metrics['phuong_acc']*100:.2f}%")
    print(f"  {'Quận Accuracy':<{pad}}: {metrics['quan_acc']*100:.2f}%")
    print(f"  {'Tỉnh/TP Accuracy':<{pad}}: {metrics['tinh_acc']*100:.2f}%")
    if "latency_mean_ms" in metrics:
        print(f"  {'Latency Mean (ms)':<{pad}}: {metrics['latency_mean_ms']:.2f}")
        print(f"  {'Latency P95 (ms)':<{pad}}: {metrics['latency_p95_ms']:.2f}")
        print(f"  {'Latency P99 (ms)':<{pad}}: {metrics['latency_p99_ms']:.2f}")
        print(f"  {'Throughput (qps)':<{pad}}: {metrics['throughput_qps']:.2f}")
    print(f"{'═'*60}")
