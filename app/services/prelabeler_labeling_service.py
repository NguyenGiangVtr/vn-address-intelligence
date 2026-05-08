"""
Shared service for PreLabeler labeling-case building and validation.

Muc tieu:
- DRY: 1 nguon logic cho random-predict va run
- SOLID: tach domain labeling/validation khoi API endpoint
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


ADMIN_PREFIX_PATTERNS = {
    "WDS": r"(Phường|Xã|Thị trấn|P\.|X\.)",
    "DST": r"(Quận|Huyện|Thị xã|Thành phố|Q\.|H\.)",
    "PRO": r"(Tỉnh|Thành phố|TP\.?)",
}

ADMIN_PRESENCE_PATTERNS = {
    "WDS": r"(?i)\b(Phường|Xã|Thị trấn|P\.|X\.)\s+",
    "DST": r"(?i)\b(Quận|Huyện|Thị xã|Thành phố|Q\.|H\.)\s+",
    "PRO": r"(?i)\b(Tỉnh|TP\.?)\s+",
}


def normalize_text(text: str) -> str:
    return str(text or "").strip().lower()


def first_expected_text(items: List[Dict[str, Any]], label: str) -> Optional[str]:
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if str(it.get("label") or "").upper() != label:
            continue
        val = str(it.get("text") or "").strip()
        if val:
            return val
    return None


def predictions_to_expected(predictions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen = set()
    for p in predictions or []:
        if not isinstance(p, dict):
            continue
        value = p.get("value") or {}
        labels = value.get("labels") or []
        label = str(labels[0] if labels else "").strip().upper()
        text = str(value.get("text") or "").strip()
        if not label or not text:
            continue
        key = (label, text.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"label": label, "text": text})
    return out


def enforce_admin_type_name(
    expected: List[Dict[str, str]],
    raw_address: str,
    ward_name: Optional[str],
    district_name: Optional[str],
    province_name: Optional[str],
) -> List[Dict[str, str]]:
    raw = str(raw_address or "")
    admin_meta = {
        "WDS": str(ward_name or "").strip(),
        "DST": str(district_name or "").strip(),
        "PRO": str(province_name or "").strip(),
    }

    items = list(expected or [])
    for label in ("WDS", "DST", "PRO"):
        name = admin_meta[label]
        if not name:
            continue

        base_name = re.sub(rf"(?i)^{ADMIN_PREFIX_PATTERNS[label]}\s*", "", name).strip()
        pat = rf"(?i)\b{ADMIN_PREFIX_PATTERNS[label]}\s+{re.escape(base_name or name)}(?!\w)"
        matched_full = None
        for m in re.finditer(pat, raw):
            matched_full = raw[m.start():m.end()].strip(" ,")

        chosen = matched_full or name
        items = [it for it in items if str(it.get("label") or "").upper() != label]
        items.append({"label": label, "text": chosen})

    out: List[Dict[str, str]] = []
    seen = set()
    for it in items:
        label = str(it.get("label") or "").strip().upper()
        text = str(it.get("text") or "").strip()
        if not label or not text:
            continue
        key = (label, text.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"label": label, "text": text})
    return out


def validate_expected_against_actual(
    raw_address: str,
    expected: List[Dict[str, Any]],
    actual: List[Dict[str, str]],
) -> Dict[str, Any]:
    details = []
    all_passed = True
    validation_errors = []

    expected_labels = {str(e.get("label") or "").upper() for e in expected if isinstance(e, dict)}
    for required_label in ("WDS", "DST", "PRO"):
        if not re.search(ADMIN_PRESENCE_PATTERNS[required_label], str(raw_address or ""), flags=re.I):
            continue
        if required_label not in expected_labels:
            validation_errors.append(f"missing_expected_admin:{required_label}")
            all_passed = False

    for exp in expected:
        label = str(exp.get("label") or "").upper()
        text = str(exp.get("text") or "").strip()
        if label in ("WDS", "DST", "PRO"):
            if _contains_prefixed_in_raw(str(raw_address or ""), label, text):
                validation_errors.append(f"admin_expected_missing_type:{label}:{text}")
                all_passed = False

        found = any(
            a.get("label") == label and normalize_text(a.get("text")) == normalize_text(text)
            for a in actual
        )
        details.append({"expected": exp, "found": found})
        if not found:
            all_passed = False

    expected_set = {
        (str(e.get("label") or "").upper(), normalize_text(str(e.get("text") or "")))
        for e in expected if isinstance(e, dict)
    }
    actual_set = {
        (str(a.get("label") or "").upper(), normalize_text(str(a.get("text") or "")))
        for a in actual if isinstance(a, dict)
    }
    unexpected = [
        {"label": lab, "text": txt}
        for (lab, txt) in actual_set
        if (lab, txt) not in expected_set
    ]
    if unexpected:
        all_passed = False

    return {
        "passed": all_passed,
        "details": details,
        "unexpected": unexpected,
        "validation_errors": validation_errors,
    }


def _contains_prefixed_in_raw(raw_text: str, label: str, expected_text: str) -> bool:
    txt = str(expected_text or "").strip()
    if not txt:
        return False
    prefix = {
        "WDS": r"(?i)^(Phường|Xã|Thị trấn|P\.|X\.)\s+",
        "DST": r"(?i)^(Quận|Huyện|Thị xã|Thành phố|Q\.|H\.)\s+",
        "PRO": r"(?i)^(Tỉnh|Thành phố|TP\.?)\s+",
    }.get(label)
    if not prefix:
        return False
    if re.search(prefix, txt):
        return False
    pat = rf"{prefix}{re.escape(txt)}(?!\w)"
    return bool(re.search(pat, raw_text or "", flags=re.I))
