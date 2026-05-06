"""
Chuẩn hóa tên đơn vị hành chính: bỏ prefix loại hình (type_name + khoảng trắng)
khớp biểu thức SQL: trim(replace(name, type_name || ' ', '')).

Dùng cho NSO sync, seed CSV/Excel, và có thể gọi từ n8n (Code node) nếu cần.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

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


def clean_admin_unit_name(name: str | None, type_name: str | None) -> str:
    if name is None:
        return ""
    raw = str(name).strip()
    if not raw:
        return ""
    t = (type_name or "").strip()
    if not t:
        return raw
    prefix = t + " "
    return raw.replace(prefix, "").strip()


def clean_mat_names_in_db(db: Session, *, dry_run: bool = False) -> dict[str, int]:
    """
    Áp dụng clean_admin_unit_name lên mat.province / district / ward (đồng bộ với SQL migration).

    Returns:
        {"province": n, "district": n, "ward": n} — số dòng sẽ/đã cập nhật.
    """
    out: dict[str, int] = {}
    try:
        for key, count_sql, update_sql in (
            ("province", _COUNT_PROVINCE_SQL, _CLEAN_PROVINCE_SQL),
            ("district", _COUNT_DISTRICT_SQL, _CLEAN_DISTRICT_SQL),
            ("ward", _COUNT_WARD_SQL, _CLEAN_WARD_SQL),
        ):
            n = db.execute(text(count_sql)).scalar_one()
            n = int(n)
            out[key] = n
            if not dry_run and n:
                db.execute(text(update_sql))
        if not dry_run:
            db.commit()
    except Exception:
        db.rollback()
        raise
    return out
