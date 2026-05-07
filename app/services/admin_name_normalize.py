"""
Chuẩn hóa tên đơn vị hành chính: bỏ prefix loại hình (type_name + khoảng trắng)
khớp biểu thức SQL: trim(replace(name, type_name || ' ', '')).

Ngoại lệ NSO: LoaiHinh "Thành phố Trung ương" nhưng tên đầy đủ vẫn là
"Thành phố …" (vd. Hà Nội) — sau bước replace, bỏ thêm tiền tố "Thành phố ".

Dùng cho NSO sync, seed CSV/Excel, và có thể gọi từ n8n (Code node) nếu cần.
Cột *_name_en / type_name_en: derive_admin_unit_*_en (remove_vietnamese_marks, strip_prefix như seed cũ).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import District, Province, Ward

_CLEAN_PROVINCE_SQL = """
UPDATE mat.province
SET province_name = trim(both FROM replace(province_name, coalesce(type_name, '') || ' ', ''))
WHERE coalesce(type_name, '') <> ''
  AND province_name IS DISTINCT FROM trim(both FROM replace(province_name, coalesce(type_name, '') || ' ', ''))
"""

_CLEAN_DISTRICT_SQL = """
UPDATE mat.district
SET district_name = trim(both FROM replace(district_name, coalesce(type_name, '') || ' ', ''))
WHERE coalesce(type_name, '') <> ''
  AND district_name IS DISTINCT FROM trim(both FROM replace(district_name, coalesce(type_name, '') || ' ', ''))
"""

_CLEAN_WARD_SQL = """
UPDATE mat.ward
SET ward_name = trim(both FROM replace(ward_name, coalesce(type_name, '') || ' ', ''))
WHERE coalesce(type_name, '') <> ''
  AND ward_name IS DISTINCT FROM trim(both FROM replace(ward_name, coalesce(type_name, '') || ' ', ''))
"""

_COUNT_PROVINCE_SQL = """
SELECT COUNT(*) FROM mat.province
WHERE coalesce(type_name, '') <> ''
  AND province_name IS DISTINCT FROM trim(both FROM replace(province_name, coalesce(type_name, '') || ' ', ''))
"""

_COUNT_DISTRICT_SQL = """
SELECT COUNT(*) FROM mat.district
WHERE coalesce(type_name, '') <> ''
  AND district_name IS DISTINCT FROM trim(both FROM replace(district_name, coalesce(type_name, '') || ' ', ''))
"""

_COUNT_WARD_SQL = """
SELECT COUNT(*) FROM mat.ward
WHERE coalesce(type_name, '') <> ''
  AND ward_name IS DISTINCT FROM trim(both FROM replace(ward_name, coalesce(type_name, '') || ' ', ''))
"""

# NSO LoaiHinh vs tên đầy đủ: type "Thành phố Trung ương" không là tiền tố của "Thành phố Hà Nội"
_THPHO_NAME_PREFIX_RE = "^Thành phố[[:space:]]+"
CENTRAL_METRO_TYPE_NAME = "Thành phố Trung ương"

_CLEAN_PROVINCE_CENTRAL_SQL = f"""
UPDATE mat.province
SET province_name = trim(both FROM regexp_replace(province_name, '{_THPHO_NAME_PREFIX_RE}', ''))
WHERE trim(both FROM coalesce(type_name, '')) = '{CENTRAL_METRO_TYPE_NAME}'
  AND province_name ~ '{_THPHO_NAME_PREFIX_RE}'
  AND province_name IS DISTINCT FROM trim(both FROM regexp_replace(province_name, '{_THPHO_NAME_PREFIX_RE}', ''))
"""

_CLEAN_DISTRICT_CENTRAL_SQL = f"""
UPDATE mat.district
SET district_name = trim(both FROM regexp_replace(district_name, '{_THPHO_NAME_PREFIX_RE}', ''))
WHERE trim(both FROM coalesce(type_name, '')) = '{CENTRAL_METRO_TYPE_NAME}'
  AND district_name ~ '{_THPHO_NAME_PREFIX_RE}'
  AND district_name IS DISTINCT FROM trim(both FROM regexp_replace(district_name, '{_THPHO_NAME_PREFIX_RE}', ''))
"""

_CLEAN_WARD_CENTRAL_SQL = f"""
UPDATE mat.ward
SET ward_name = trim(both FROM regexp_replace(ward_name, '{_THPHO_NAME_PREFIX_RE}', ''))
WHERE trim(both FROM coalesce(type_name, '')) = '{CENTRAL_METRO_TYPE_NAME}'
  AND ward_name ~ '{_THPHO_NAME_PREFIX_RE}'
  AND ward_name IS DISTINCT FROM trim(both FROM regexp_replace(ward_name, '{_THPHO_NAME_PREFIX_RE}', ''))
"""

_COUNT_PROVINCE_CENTRAL_SQL = f"""
SELECT COUNT(*) FROM mat.province
WHERE trim(both FROM coalesce(type_name, '')) = '{CENTRAL_METRO_TYPE_NAME}'
  AND province_name ~ '{_THPHO_NAME_PREFIX_RE}'
  AND province_name IS DISTINCT FROM trim(both FROM regexp_replace(province_name, '{_THPHO_NAME_PREFIX_RE}', ''))
"""

_COUNT_DISTRICT_CENTRAL_SQL = f"""
SELECT COUNT(*) FROM mat.district
WHERE trim(both FROM coalesce(type_name, '')) = '{CENTRAL_METRO_TYPE_NAME}'
  AND district_name ~ '{_THPHO_NAME_PREFIX_RE}'
  AND district_name IS DISTINCT FROM trim(both FROM regexp_replace(district_name, '{_THPHO_NAME_PREFIX_RE}', ''))
"""

_COUNT_WARD_CENTRAL_SQL = f"""
SELECT COUNT(*) FROM mat.ward
WHERE trim(both FROM coalesce(type_name, '')) = '{CENTRAL_METRO_TYPE_NAME}'
  AND ward_name ~ '{_THPHO_NAME_PREFIX_RE}'
  AND ward_name IS DISTINCT FROM trim(both FROM regexp_replace(ward_name, '{_THPHO_NAME_PREFIX_RE}', ''))
"""


def clean_admin_unit_name(name: str | None, type_name: str | None) -> str:
    if name is None:
        return ""
    raw = str(name).strip()
    if not raw:
        return ""
    t = (type_name or "").strip()
    if t:
        raw = raw.replace(t + " ", "").strip()
    if t == CENTRAL_METRO_TYPE_NAME and raw.startswith("Thành phố "):
        raw = raw.removeprefix("Thành phố ").strip()
    return raw


def _remove_vietnamese_marks_slug(s: str | None, *, strip_prefix: bool = True) -> str:
    """Lazy-import để tránh vòng import với seeders_v3."""
    from app.services.seeders_v3 import remove_vietnamese_marks

    if not s:
        return ""
    return remove_vietnamese_marks(str(s).strip(), strip_prefix=strip_prefix)


def derive_admin_unit_name_en(cleaned_vietnamese_name: str | None) -> str:
    """*_name_en từ tên tiếng Việt đã qua clean_admin_unit_name."""
    return _remove_vietnamese_marks_slug(cleaned_vietnamese_name, strip_prefix=True)


def derive_admin_unit_name_en_from_raw(raw_name: str | None, type_name: str | None) -> str:
    """*_name_en từ tên thô NSO/import + LoaiHinh."""
    return derive_admin_unit_name_en(clean_admin_unit_name(raw_name, type_name))


def derive_admin_type_name_en(type_name_vietnamese: str | None) -> str:
    """type_name_en từ type_name tiếng Việt."""
    return _remove_vietnamese_marks_slug(type_name_vietnamese, strip_prefix=False)


def refresh_mat_admin_name_en_columns(db: Session, *, dry_run: bool = False) -> dict[str, int]:
    """
    Đồng bộ province_name_en, district_name_en + type_name_en, ward_name_en + type_name_en
    từ các cột tên tiếng Việt / type hiện tại (đã là bản đã clean).
    """
    out = {"province_name_en": 0, "district_name_en": 0, "ward_name_en": 0}
    for p in db.query(Province).all():
        en = derive_admin_unit_name_en(p.province_name or "")
        if (p.province_name_en or "") != en:
            out["province_name_en"] += 1
            if not dry_run:
                p.province_name_en = en
    for d in db.query(District).all():
        ne = derive_admin_unit_name_en(d.district_name or "")
        te = derive_admin_type_name_en(d.type_name)
        touched = False
        if (d.district_name_en or "") != ne:
            touched = True
            if not dry_run:
                d.district_name_en = ne
        if (d.type_name_en or "") != te:
            touched = True
            if not dry_run:
                d.type_name_en = te
        if touched:
            out["district_name_en"] += 1
    for w in db.query(Ward).all():
        ne = derive_admin_unit_name_en(w.ward_name or "")
        te = derive_admin_type_name_en(w.type_name)
        touched = False
        if (w.ward_name_en or "") != ne:
            touched = True
            if not dry_run:
                w.ward_name_en = ne
        if (w.type_name_en or "") != te:
            touched = True
            if not dry_run:
                w.type_name_en = te
        if touched:
            out["ward_name_en"] += 1
    return out


def clean_mat_names_in_db(db: Session, *, dry_run: bool = False) -> dict[str, int]:
    """
    Áp dụng clean_admin_unit_name lên mat.province / district / ward (đồng bộ với SQL migration).

    Returns:
        Số dòng sẽ/đã cập nhật theo từng bước (province/district/ward,
        *_central_tp, và đồng bộ *_name_en / type_name_en từ remove_vietnamese_marks).
    """
    out: dict[str, int] = {}
    try:
        for key, count_sql, update_sql in (
            ("province", _COUNT_PROVINCE_SQL, _CLEAN_PROVINCE_SQL),
            ("district", _COUNT_DISTRICT_SQL, _CLEAN_DISTRICT_SQL),
            ("ward", _COUNT_WARD_SQL, _CLEAN_WARD_SQL),
            ("province_central_tp", _COUNT_PROVINCE_CENTRAL_SQL, _CLEAN_PROVINCE_CENTRAL_SQL),
            ("district_central_tp", _COUNT_DISTRICT_CENTRAL_SQL, _CLEAN_DISTRICT_CENTRAL_SQL),
            ("ward_central_tp", _COUNT_WARD_CENTRAL_SQL, _CLEAN_WARD_CENTRAL_SQL),
        ):
            n = db.execute(text(count_sql)).scalar_one()
            n = int(n)
            out[key] = n
            if not dry_run and n:
                db.execute(text(update_sql))
        en_counts = refresh_mat_admin_name_en_columns(db, dry_run=dry_run)
        out.update(en_counts)
        if not dry_run:
            db.commit()
    except Exception:
        db.rollback()
        raise
    return out
