"""
metrics.py
==========
Tập hợp các hàm đo lường chất lượng chuẩn hóa địa chỉ:
- Exact Match (EM)
- Levenshtein / Normalized Edit Distance
- Component Accuracy (Đường / Phường / Quận / Tỉnh)
- Component F1 (TP/FP/FN per cấp; FP = dự đoán có thành phần khi GT rỗng)
- Latency statistics + throughput (addr/s)
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

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
# Phần đường / số nhà: đoạn trước dấu phẩy đầu, bỏ tiền tố số nhà kiểu "123A / ".
_STREET_LEAD_NUM = re.compile(r"^\s*\d+[A-Za-z]?[\./\-]?\s*", re.UNICODE)


def parse_street_line1(address: str) -> str:
    """Đoạn đường (line-1): trước dấu phẩy đầu, đã bỏ số nhà đầu dòng."""
    if not (address or "").strip():
        return ""
    first = address.split(",")[0].strip()
    first = _STREET_LEAD_NUM.sub("", first).strip()
    return first


def parse_components(address: str) -> Dict[str, str]:
    """Tách thô các thành phần: đường (line-1) + Phường / Quận / Tỉnh."""
    parts: Dict[str, str] = {"duong": "", "phuong": "", "quan": "", "tinh": ""}
    if not address:
        return parts
    parts["duong"] = parse_street_line1(address)
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


COMPONENT_LEVEL_KEYS: Tuple[str, ...] = ("duong", "phuong", "quan", "tinh")


def _comp_nonempty(raw: str) -> bool:
    return bool((raw or "").strip())


def _tp_fp_fn_one(pred: str, gt: str, level: str) -> Tuple[int, int, int]:
    pc = parse_components(pred or "")
    gc = parse_components(gt or "")
    pv = _normalize_str(pc.get(level, "") or "")
    gv = _normalize_str(gc.get(level, "") or "")
    g_has = _comp_nonempty(gc.get(level, ""))
    p_has = _comp_nonempty(pc.get(level, ""))
    if g_has and gv == pv:
        return 1, 0, 0
    if g_has:
        return 0, 0, 1
    if p_has:
        return 0, 1, 0
    return 0, 0, 0


def aggregate_tp_fp_fn(
    predictions: List[str], ground_truths: List[str], level: str
) -> Dict[str, float]:
    tp = fp = fn = 0
    for pred, gt in zip(predictions, ground_truths):
        t, f, n = _tp_fp_fn_one(pred, gt, level)
        tp += t
        fp += f
        fn += n
    pr = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rc = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * pr * rc / (pr + rc)) if (pr + rc) > 0 else 0.0
    return {
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "precision": float(pr),
        "recall": float(rc),
        "f1": float(f1),
    }


def compute_component_f1_bundle(
    predictions: List[str], ground_truths: List[str]
) -> Dict[str, Any]:
    """F1 riêng từng cấp (đường / phường / quận / tỉnh) trên toàn tập."""
    out: Dict[str, Any] = {}
    for lvl in COMPONENT_LEVEL_KEYS:
        stats = aggregate_tp_fp_fn(predictions, ground_truths, lvl)
        out[lvl] = stats
    return out


def _norm_em_supa(s: str | None) -> str:
    """Giống SUPA eval: NFC + gộp khoảng trắng (không bỏ dấu)."""
    t = unicodedata.normalize("NFC", (s or "").strip())
    t = re.sub(r"\s+", " ", t)
    return t


def supa_strings_exact_match(pred: str | None, ref: str | None) -> bool:
    """True nếu pred và ref khớp tuyệt đối theo quy tắc EM SUPA (NFC/trim/gộp khoảng trắng)."""
    return _norm_em_supa(pred) == _norm_em_supa(ref)


def _latency_stats_from_optional(latencies: List[Any]) -> Dict[str, float]:
    vals: List[float] = []
    for v in latencies:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if not vals:
        return {}
    arr = np.array(vals, dtype=float)
    mean_ms = float(np.mean(arr))
    return {
        "latency_mean_ms": round(mean_ms, 4),
        "latency_p95_ms": round(float(np.percentile(arr, 95)), 4),
        "latency_p99_ms": round(float(np.percentile(arr, 99)), 4),
        "throughput_qps": round(float(1000.0 / mean_ms) if mean_ms > 0 else 0.0, 4),
        "throughput_addr_per_s": round(float(1000.0 / mean_ms) if mean_ms > 0 else 0.0, 4),
        "n_latency_samples": int(len(vals)),
    }


def compute_supa_quality_metrics(
    predictions: List[str],
    ground_truths_v2: List[str],
    latencies_ms: Optional[List[float]] = None,
    ground_truths_v1: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Gói metrics cho SUPA eval: EM@v2/v1 (%), component F1 (%), latency, throughput addr/s.
    `latencies_ms` optional; nếu có thì throughput = 1000/mean(ms) (addr/s).
    """
    n = len(predictions)
    assert len(ground_truths_v2) == n
    if ground_truths_v1 is not None:
        assert len(ground_truths_v1) == n

    em_v2 = em_v1 = None
    if n > 0:
        ok2 = sum(
            1
            for p, g in zip(predictions, ground_truths_v2)
            if _norm_em_supa(p) == _norm_em_supa(g)
        )
        em_v2 = round(100.0 * ok2 / n, 4)
        if ground_truths_v1 is not None:
            ok1 = sum(
                1
                for p, g in zip(predictions, ground_truths_v1)
                if _norm_em_supa(p) == _norm_em_supa(g)
            )
            em_v1 = round(100.0 * ok1 / n, 4)

    f1_bundle = compute_component_f1_bundle(predictions, ground_truths_v2)
    flat: Dict[str, Any] = {}
    for lvl, st in f1_bundle.items():
        flat[f"f1_{lvl}_pct"] = round(100.0 * float(st["f1"]), 4)
        flat[f"precision_{lvl}_pct"] = round(100.0 * float(st["precision"]), 4)
        flat[f"recall_{lvl}_pct"] = round(100.0 * float(st["recall"]), 4)
        flat[f"tp_{lvl}"] = int(st["tp"])
        flat[f"fp_{lvl}"] = int(st["fp"])
        flat[f"fn_{lvl}"] = int(st["fn"])

    lat_block: Dict[str, Any] = {}
    if latencies_ms is not None and len(latencies_ms) == n:
        lat_block = _latency_stats_from_optional(list(latencies_ms))

    return {
        "n_samples": n,
        "em_v2_pct": em_v2,
        "em_v1_pct": em_v1,
        "component_f1": f1_bundle,
        **flat,
        **lat_block,
    }


def compute_metrics_by_stratum(
    rows: List[Dict[str, Any]],
    pred_key: str = "pred_standardized",
    ref_v2_key: str = "ref_address_v2",
    ref_v1_key: str = "ref_address_v1",
    stratum_key: str = "stratum_code",
    latency_key: str = "latency_ms",
) -> Dict[str, Any]:
    """
    rows: mỗi phần tử dict có stratum_code (có thể None), pred, ref, latency_ms tùy chọn.
    Trả về metrics giống compute_supa_quality_metrics nhưng lồng theo stratum.
    """
    by: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        code = (r.get(stratum_key) or "").strip() or "UNLABELED"
        by.setdefault(code, []).append(r)

    out: Dict[str, Any] = {}
    for code, grp in sorted(by.items()):
        preds = [str(r.get(pred_key) or "") for r in grp]
        refs2 = [str(r.get(ref_v2_key) or "") for r in grp]
        refs1 = [str(r.get(ref_v1_key) or "") for r in grp]
        lat = [r.get(latency_key) for r in grp]
        lat_f: Optional[List[Any]] = lat if len(lat) == len(preds) else None
        out[code] = compute_supa_quality_metrics(
            preds, refs2, latencies_ms=lat_f, ground_truths_v1=refs1
        )
    return out


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
    comp_hits = {"duong": 0, "phuong": 0, "quan": 0, "tinh": 0}
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
        mean_ms = float(np.mean(arr))
        lat_stats = {
            "latency_mean_ms": float(mean_ms),
            "latency_p95_ms":  float(np.percentile(arr, 95)),
            "latency_p99_ms":  float(np.percentile(arr, 99)),
            "throughput_qps":  float(1000.0 / mean_ms) if mean_ms > 0 else 0.0,
            "throughput_addr_per_s": float(1000.0 / mean_ms) if mean_ms > 0 else 0.0,
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
        "duong_acc":       comp_hits["duong"]   / max(_denom("duong"), 1),
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
    print(f"    {model_name}")
    print(f"{'═'*60}")
    print(f"  {'Samples':<{pad}}: {metrics['n_samples']}")
    print(f"  {'Exact Match':<{pad}}: {metrics['exact_match']*100:.2f}%")
    print(f"  {'Fuzzy Match (≥0.85)':<{pad}}: {metrics['fuzzy_match']*100:.2f}%")
    print(f"  {'Levenshtein Score (mean)':<{pad}}: {metrics['lev_score_mean']:.4f}")
    print(f"  {'Đường Accuracy':<{pad}}: {metrics.get('duong_acc', 0)*100:.2f}%")
    print(f"  {'Phường Accuracy':<{pad}}: {metrics['phuong_acc']*100:.2f}%")
    print(f"  {'Quận Accuracy':<{pad}}: {metrics['quan_acc']*100:.2f}%")
    print(f"  {'Tỉnh/TP Accuracy':<{pad}}: {metrics['tinh_acc']*100:.2f}%")
    if "latency_mean_ms" in metrics:
        print(f"  {'Latency Mean (ms)':<{pad}}: {metrics['latency_mean_ms']:.2f}")
        print(f"  {'Latency P95 (ms)':<{pad}}: {metrics['latency_p95_ms']:.2f}")
        print(f"  {'Latency P99 (ms)':<{pad}}: {metrics['latency_p99_ms']:.2f}")
        print(f"  {'Throughput (qps)':<{pad}}: {metrics['throughput_qps']:.2f}")
    print(f"{'═'*60}")
