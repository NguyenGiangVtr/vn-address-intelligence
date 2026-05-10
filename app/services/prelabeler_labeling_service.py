"""
Shared service for PreLabeler labeling-case building and validation.

Muc tieu:
- DRY: 1 nguon logic cho random-predict va run
- SOLID: tach domain labeling/validation khoi API endpoint

Bo tien to admin (WDS/DST/PRO) duoc dinh nghia DUY NHAT tai
`app.ai.constants` (ADMIN_PREFIX_ALTERNATIVES, ADMIN_PRESENCE_ALTERNATIVES).
File nay KHONG duoc khai bao lai vocabulary admin prefix.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.ai.constants import (
    ADMIN_PREFIX_ALTERNATIVES,
    admin_prefix_anchored_pattern,
    admin_presence_pattern,
)


# Cac bien duoi day chi la pattern compose tu canonical alternatives, KHONG
# duoc viet lai vocabulary. Sua canonical tai app.ai.constants.
ADMIN_PREFIX_PATTERNS = {
    label: rf"({alts})" for label, alts in ADMIN_PREFIX_ALTERNATIVES.items()
}

ADMIN_PRESENCE_PATTERNS = {
    label: admin_presence_pattern(label) for label in ADMIN_PREFIX_ALTERNATIVES
}
ADMIN_ALL_PREFIXES_ALT = "|".join(
    f"(?:{alts})" for alts in ADMIN_PREFIX_ALTERNATIVES.values() if str(alts).strip()
)


def normalize_text(text: str) -> str:
    return str(text or "").strip().lower()


def admin_entity_text_equivalent(label: str, expected_text: str, actual_text: str) -> bool:
    """So khớp WDS/DST/PRO khi một bên có tiền tố Type+Name và bên kia chỉ tên (canonical trong suite)."""
    lab = str(label or "").upper()
    if lab not in ("WDS", "DST", "PRO"):
        return False
    exp = str(expected_text or "").strip()
    act = str(actual_text or "").strip()
    if normalize_text(exp) == normalize_text(act):
        return True
    alts = ADMIN_PREFIX_ALTERNATIVES.get(lab)
    if not alts:
        return False
    strip_re = rf"(?i)^(?:{alts})\s+"

    def _strip_admin_prefix(s: str) -> str:
        t = str(s or "").strip()
        return re.sub(strip_re, "", t, count=1).strip()

    eb = _strip_admin_prefix(exp)
    ab = _strip_admin_prefix(act)
    if not eb or not ab:
        return False
    eb_n = normalize_text(eb)
    ab_n = normalize_text(ab)
    if lab == "PRO":
        pro_key = {
            "thành phố trung ương hồ chí minh": "hồ chí minh",
            "uảng nam": "quảng nam",
            "quang nam province": "quảng nam",
            "quang nam": "quảng nam",
        }
        eb_n = pro_key.get(eb_n, eb_n)
        ab_n = pro_key.get(ab_n, ab_n)
    return eb_n == ab_n


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

    def _resolve_prefixed_from_raw(label: str, text_val: str) -> Optional[str]:
        txt = str(text_val or "").strip()
        if not txt:
            return None
        # Neu text da co prefix dung nhan va xuat hien trong raw -> giu nguyen.
        # Rieng PRO: can di tiep qua disambiguation khi trung ten DST/PRO.
        pref_pat = admin_prefix_anchored_pattern(label)
        if label != "PRO" and pref_pat and re.search(pref_pat, txt, flags=re.I):
            return txt

        base_name = re.sub(rf"(?i)^{ADMIN_PREFIX_PATTERNS[label]}\s*", "", txt).strip()
        if label == "PRO" and ADMIN_ALL_PREFIXES_ALT:
            # Bo them cac tien to admin cap khac de xu ly ten trung cap (DST ~ PRO).
            base_name = re.sub(rf"(?i)^(?:{ADMIN_ALL_PREFIXES_ALT})\s*", "", base_name).strip() or base_name
        if not base_name:
            return None

        # Disambiguation cho PRO khi ten thanh pho trung ten tinh:
        # vd "... Thành Phố Trà Vinh, Trà Vinh" -> PRO phai la "Trà Vinh".
        if label == "PRO":
            bare_seg_pat = rf"(?i)(?:^|,)\s*({re.escape(base_name)})\s*(?=,|$)"
            bare_matches = list(re.finditer(bare_seg_pat, raw))
            if bare_matches:
                # Lay segment phai nhat (thuong la phan tinh o cuoi dia chi).
                m = bare_matches[-1]
                return (m.group(1) or "").strip() or txt

        pat = rf"(?i)\b{ADMIN_PREFIX_PATTERNS[label]}\s+{re.escape(base_name)}(?!\w)"
        matched_full = None
        for m in re.finditer(pat, raw):
            matched_full = raw[m.start():m.end()].strip(" ,")
        if matched_full:
            return matched_full

        # Fallback quan trong cho random-predict:
        # Neu metadata tra ve ma ngan (vd "01") hoac ten khong match raw,
        # nhung raw co cum admin prefixed ro rang, uu tien cum trong raw.
        generic_pat = rf"(?i)\b{ADMIN_PREFIX_PATTERNS[label]}\s+[^,\n]+"
        generic_matches = [raw[m.start():m.end()].strip(" ,") for m in re.finditer(generic_pat, raw)]
        if generic_matches:
            txt_norm = txt.strip().lower()
            is_code_like = bool(re.fullmatch(r"[0-9A-Za-z]{1,3}", txt_norm))
            if is_code_like:
                return generic_matches[-1]
            # Kể cả không phải mã, nếu text hiện tại không chứa prefix mà raw có prefix rõ,
            # ưu tiên chuẩn Type+Name từ raw để đồng nhất hiển thị/annotated.
            if not (pref_pat and re.search(pref_pat, txt, flags=re.I)):
                return generic_matches[-1]

        return txt
    for label in ("WDS", "DST", "PRO"):
        name = admin_meta[label]
        if not name:
            continue
        chosen = _resolve_prefixed_from_raw(label, name) or str(name).strip()
        items = [it for it in items if str(it.get("label") or "").upper() != label]
        items.append({"label": label, "text": chosen})

    # Truong hop random-predict khong co admin metadata day du (hoac metadata khong co prefix):
    # van nang cap expected admin hien co len "Type + Name" neu raw co chuoi prefixed.
    for label in ("WDS", "DST", "PRO"):
        has_meta = bool(admin_meta.get(label))
        if has_meta:
            continue
        for it in items:
            if str(it.get("label") or "").upper() != label:
                continue
            txt = str(it.get("text") or "").strip()
            resolved = _resolve_prefixed_from_raw(label, txt)
            if resolved and normalize_text(resolved) != normalize_text(txt):
                it["text"] = resolved

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
            a.get("label") == label
            and (
                normalize_text(a.get("text")) == normalize_text(text)
                or admin_entity_text_equivalent(label, text, str(a.get("text") or ""))
            )
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
    def _actual_unused_admin(lab: str, raw_txt: str) -> bool:
        if lab not in ("WDS", "DST", "PRO"):
            return True
        for e in expected:
            if not isinstance(e, dict):
                continue
            if str(e.get("label") or "").upper() != lab:
                continue
            if admin_entity_text_equivalent(lab, str(e.get("text") or ""), raw_txt):
                return False
        return True

    unexpected = [
        {"label": lab, "text": txt}
        for (lab, txt) in actual_set
        if (lab, txt) not in expected_set
        and _actual_unused_admin(lab, txt)
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
    prefix = admin_prefix_anchored_pattern(label)
    if not prefix:
        return False
    if re.search(prefix, txt):
        return False
    pat = rf"{prefix}{re.escape(txt)}(?!\w)"
    return bool(re.search(pat, raw_text or "", flags=re.I))
