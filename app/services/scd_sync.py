from __future__ import annotations
"""
services/scd_sync.py
====================
Đồng bộ thay đổi đơn vị hành chính trên `mat.*` theo quy ước:

- Mỗi `province_id` / `district_id` / `ward_id` chỉ có **tối đa một** dòng
  `is_deleted = false` (enforce bằng UNIQUE partial index sau migration).
- Dòng đại diện hiện tại trên UI/API: `is_active = true`.
- Khi đổi nội dung có mã nghiệp vụ mới: tắt `is_active` bản cũ, insert bản mới
  với `new_{level}_id` (xem tham số `unit_data`).

Quy trình (cập nhật có thay đổi checksum):
  1. Tìm bản ghi `is_active = true` và `is_deleted = false` theo mã hiện tại.
  2. So checksum; nếu khác: đóng bản cũ (`valid_to`, `is_active = false`).
  3. Insert bản mới với **`new_province_id` / `new_district_id` / `new_ward_id`**
     (bắt buộc) — khác mã bản đang active.
  4. Ghi `ath.sync_log`.

Ví dụ:
-------
from app.services.scd_sync import scd_upsert_unit
from app.core.database import SessionLocal
from datetime import datetime

db = SessionLocal()
effective = datetime.now()
result = scd_upsert_unit(
    db,
    "ward",
    {
        "ward_id": 770001,
        "new_ward_id": 770099,
        "ward_name": "Phường Mới",
        "district_id": 123,
        "province_no": "01",
    },
    effective,
)
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.database import Province, District, Ward, SyncLog, UnitEdge


# ── Helpers ─────────────────────────────────────────────────────────────────

_SCD_CHECKSUM_FIELDS = {
    "province": [
        "province_name",
        "province_name_en",
        "type_name",
        "population",
        "area_km2",
        "decision_number",
        "notes",
    ],
    "district": [
        "district_name",
        "district_name_en",
        "type_name",
        "type_name_en",
        "province_id",
        "population",
        "area_km2",
        "decision_number",
        "notes",
    ],
    "ward": [
        "ward_name",
        "ward_name_en",
        "type_name",
        "type_name_en",
        "district_id",
        "province_no",
        "population",
        "area_km2",
        "decision_number",
        "notes",
    ],
}

_MODEL_MAP = {
    "province": Province,
    "district": District,
    "ward": Ward,
}

_ID_FIELD_MAP = {
    "province": "province_id",
    "district": "district_id",
    "ward": "ward_id",
}

_NEW_BUSINESS_ID_KEY = {
    "province": "new_province_id",
    "district": "new_district_id",
    "ward": "new_ward_id",
}


def _compute_checksum(data: dict, fields: List[str]) -> str:
    """Tính SHA-256 checksum từ các trường theo dõi thay đổi."""
    payload = {f: str(data.get(f, "")) for f in fields}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _model_to_dict(obj, fields: List[str]) -> dict:
    """Chuyển SQLAlchemy model object sang dict với các trường chỉ định."""
    return {f: getattr(obj, f, None) for f in fields}


def _filter_model_kwargs(model_cls, data: dict) -> dict:
    """Chỉ giữ key trùng cột ORM; bỏ khóa phụ trừ (`new_*_id`)."""
    skip = set(_NEW_BUSINESS_ID_KEY.values())
    return {k: v for k, v in data.items() if hasattr(model_cls, k) and k not in skip}


# ── Core ─────────────────────────────────────────────────────────────────────


def scd_upsert_unit(
    db: Session,
    level: str,
    unit_data: dict,
    effective_date: datetime,
    sync_source: str = "N8N_WORKFLOW",
    run_id: Optional[str] = None,
) -> dict:
    """
    Upsert đơn vị hành chính theo quy ước `is_active` + mã nghiệp vụ duy nhất (alive).

    `unit_data` phải có `{level}_id` — mã của bản ghi **đang active** cần so khớp
    (hoặc mã mới khi CREATE).

    Khi có thay đổi nội dung (checksum khác) so với bản active: phải có
    `new_province_id` | `new_district_id` | `new_ward_id` tương ứng `level`,
    khác `{level}_id` của bản active hiện tại.
    """
    if level not in _MODEL_MAP:
        raise ValueError(f"level phải là một trong: {list(_MODEL_MAP.keys())}")

    Model = _MODEL_MAP[level]
    id_field = _ID_FIELD_MAP[level]
    new_id_field = _NEW_BUSINESS_ID_KEY[level]
    checksum_fields = _SCD_CHECKSUM_FIELDS[level]
    run_id = run_id or str(uuid.uuid4())

    unit_id = unit_data.get(id_field)
    if unit_id is None:
        raise ValueError(f"unit_data phải có trường '{id_field}'")

    existing = (
        db.query(Model)
        .filter(
            getattr(Model, id_field) == unit_id,
            Model.is_active == True,
            Model.is_deleted == False,
        )
        .first()
    )

    change_type = "NO_CHANGE"
    old_snapshot = None
    new_snapshot = None

    if existing:
        old_snapshot = _model_to_dict(existing, checksum_fields)
        checksum_old = _compute_checksum(old_snapshot, checksum_fields)
        checksum_new = _compute_checksum(unit_data, checksum_fields)

        if checksum_old == checksum_new:
            _write_sync_log(db, sync_source, level, unit_id, "NO_CHANGE", None, None, run_id)
            db.commit()
            return {"change_type": "NO_CHANGE", "unit_id": unit_id}

        new_business_id = unit_data.get(new_id_field)
        if new_business_id is None:
            raise ValueError(
                f"Khi cập nhật có thay đổi nội dung, unit_data phải có '{new_id_field}' "
                f"(mã nghiệp vụ mới, khác '{id_field}' của bản active hiện tại)."
            )
        if int(new_business_id) == int(getattr(existing, id_field)):
            raise ValueError(
                f"'{new_id_field}' phải khác '{id_field}' của bản ghi đang active "
                f"(ràng buộc UNIQUE trên mã alive)."
            )

        existing.valid_to = effective_date
        existing.is_active = False
        change_type = "UPDATE"
        new_snapshot = {k: unit_data.get(k) for k in checksum_fields}
    else:
        change_type = "CREATE"
        new_snapshot = {k: unit_data.get(k) for k in checksum_fields}

    new_business_id_for_row = (
        int(unit_data[new_id_field])
        if change_type == "UPDATE"
        else int(unit_id)
    )

    new_record_data = _filter_model_kwargs(Model, unit_data)
    new_record_data[id_field] = new_business_id_for_row
    new_record_data["valid_from"] = effective_date
    new_record_data["valid_to"] = datetime(9999, 12, 31)
    new_record_data["is_active"] = True
    new_record_data["is_deleted"] = False
    new_record_data["version_id"] = (existing.version_id + 1) if existing else 1
    new_record_data["predecessor_id"] = existing.row_id if existing else None

    new_record = Model(**new_record_data)
    db.add(new_record)

    _write_sync_log(db, sync_source, level, unit_id, change_type, old_snapshot, new_snapshot, run_id)
    db.commit()

    return {
        "change_type": change_type,
        "unit_id": unit_id,
        "new_business_id": new_business_id_for_row,
        "old_version": old_snapshot,
        "new_version": new_snapshot,
    }


def _write_sync_log(
    db: Session,
    sync_source: str,
    level: str,
    unit_id: int,
    change_type: str,
    old_value: Optional[dict],
    new_value: Optional[dict],
    run_id: str,
) -> None:
    """Ghi một bản ghi vào ath.sync_log."""
    log = SyncLog(
        sync_source=sync_source,
        level=level,
        unit_id=unit_id,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        synced_at=datetime.now(),
        records_affected=1,
        run_id=run_id,
    )
    db.add(log)


# ── History Query ────────────────────────────────────────────────────────────


def get_unit_at_date(db: Session, level: str, unit_id: int, at: Optional[datetime] = None):
    """
    Lấy trạng thái đơn vị hành chính tại thời điểm `at`.
    Nếu `at` là None, trả về toàn bộ lịch sử theo thứ tự version_id.
    """
    if level not in _MODEL_MAP:
        raise ValueError(f"level phải là một trong: {list(_MODEL_MAP.keys())}")

    Model = _MODEL_MAP[level]
    id_field = _ID_FIELD_MAP[level]

    if at:
        return (
            db.query(Model)
            .filter(
                getattr(Model, id_field) == unit_id,
                Model.valid_from <= at,
                Model.valid_to > at,
            )
            .first()
        )
    return (
        db.query(Model)
        .filter(getattr(Model, id_field) == unit_id)
        .order_by(Model.version_id)
        .all()
    )


# ── Edge Registration ────────────────────────────────────────────────────────


def register_unit_edge(
    db: Session,
    from_unit_id: int,
    from_level: str,
    to_unit_id: int,
    to_level: str,
    relationship_type: str,
    effective_date: datetime,
    resolution_ref: Optional[str] = None,
    notes: Optional[str] = None,
) -> UnitEdge:
    """
    Ghi quan hệ thay đổi hành chính vào mat.unit_edge.

    relationship_type: MERGES_INTO | SPLIT_FROM | RENAMES_TO | BOUNDARY_ADJUSTED
    """
    edge = UnitEdge(
        from_unit_id=from_unit_id,
        from_level=from_level,
        to_unit_id=to_unit_id,
        to_level=to_level,
        relationship_type=relationship_type,
        effective_date=effective_date,
        resolution_ref=resolution_ref,
        notes=notes,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


# ── Batch Sync Summary ───────────────────────────────────────────────────────


def get_sync_summary(db: Session, run_id: str) -> dict:
    """
    Tổng hợp kết quả một lần chạy đồng bộ theo run_id.
    Returns dict với số lượng theo change_type.
    """
    logs = db.query(SyncLog).filter(SyncLog.run_id == run_id).all()
    summary: dict = {
        "run_id": run_id,
        "total": len(logs),
        "CREATE": 0,
        "UPDATE": 0,
        "NO_CHANGE": 0,
        "by_level": {},
    }
    for log in logs:
        ct = log.change_type or "UNKNOWN"
        summary[ct] = summary.get(ct, 0) + 1
        lvl = log.level or "unknown"
        if lvl not in summary["by_level"]:
            summary["by_level"][lvl] = {"CREATE": 0, "UPDATE": 0, "NO_CHANGE": 0}
        summary["by_level"][lvl][ct] = summary["by_level"][lvl].get(ct, 0) + 1
    return summary
