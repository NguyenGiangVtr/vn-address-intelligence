"""
services/scd_sync.py
====================
SCD Type 2 (Slowly Changing Dimension Type 2) upsert logic cho đơn vị hành chính.

Quy trình:
  1. Tìm bản ghi is_current=True theo unit_id
  2. Tính checksum để phát hiện thay đổi thực sự
  3. Nếu có thay đổi: đóng bản ghi cũ (valid_to=now, is_current=False)
  4. Tạo bản ghi mới với valid_from=now, is_current=True, version_id+1
  5. Ghi log vào ath.sync_log

Ví dụ thực thi:
--------------
from app.services.scd_sync import scd_upsert_unit, get_unit_at_date
from app.core.database import SessionLocal
from datetime import datetime

db = SessionLocal()
effective = datetime.now()
result = scd_upsert_unit(db, 'ward', {'ward_id': 770001, 'ward_name': 'Phường Mới'}, effective)
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import Province, District, Ward, SyncLog, UnitEdge


# ── Helpers ─────────────────────────────────────────────────────────────────

_SCD_CHECKSUM_FIELDS = {
    'province': ['province_name', 'province_name_en', 'type_name', 'population', 'area_km2', 'decision_number', 'notes'],
    'district': ['district_name', 'district_name_en', 'type_name', 'province_id', 'population', 'area_km2', 'decision_number', 'notes'],
    'ward': ['ward_name', 'ward_name_en', 'type_name', 'district_id', 'province_no', 'population', 'area_km2', 'decision_number', 'notes'],
}

_MODEL_MAP = {
    'province': Province,
    'district': District,
    'ward': Ward,
}

_ID_FIELD_MAP = {
    'province': 'province_id',
    'district': 'district_id',
    'ward': 'ward_id',
}


def _compute_checksum(data: dict, fields: list[str]) -> str:
    """Tính SHA-256 checksum từ các trường theo dõi thay đổi."""
    payload = {f: str(data.get(f, '')) for f in fields}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _model_to_dict(obj, fields: list[str]) -> dict:
    """Chuyển SQLAlchemy model object sang dict với các trường chỉ định."""
    return {f: getattr(obj, f, None) for f in fields}


# ── Core SCD Type 2 ──────────────────────────────────────────────────────────

def scd_upsert_unit(
    db: Session,
    level: str,
    unit_data: dict,
    effective_date: datetime,
    sync_source: str = 'N8N_WORKFLOW',
    run_id: Optional[str] = None,
) -> dict:
    """
    Thực hiện SCD Type 2 upsert cho một đơn vị hành chính.

    Args:
        db:             SQLAlchemy session
        level:          'province' | 'district' | 'ward'
        unit_data:      dict dữ liệu đơn vị (phải có {level}_id)
        effective_date: Thời điểm hiệu lực của thay đổi
        sync_source:    Nguồn đồng bộ ghi vào sync_log
        run_id:         UUID nhóm log cùng một lần chạy

    Returns:
        dict với keys: change_type, old_version, new_version
    """
    if level not in _MODEL_MAP:
        raise ValueError(f"level phải là một trong: {list(_MODEL_MAP.keys())}")

    Model = _MODEL_MAP[level]
    id_field = _ID_FIELD_MAP[level]
    checksum_fields = _SCD_CHECKSUM_FIELDS[level]
    run_id = run_id or str(uuid.uuid4())

    unit_id = unit_data.get(id_field)
    if unit_id is None:
        raise ValueError(f"unit_data phải có trường '{id_field}'")

    existing = (
        db.query(Model)
        .filter(
            getattr(Model, id_field) == unit_id,
            Model.is_current == True,
        )
        .first()
    )

    change_type = 'NO_CHANGE'
    old_snapshot = None
    new_snapshot = None

    if existing:
        old_snapshot = _model_to_dict(existing, checksum_fields)
        checksum_old = _compute_checksum(old_snapshot, checksum_fields)
        checksum_new = _compute_checksum(unit_data, checksum_fields)

        if checksum_old == checksum_new:
            _write_sync_log(db, sync_source, level, unit_id, 'NO_CHANGE', None, None, run_id)
            db.commit()
            return {'change_type': 'NO_CHANGE', 'unit_id': unit_id}

        # Đóng bản ghi cũ
        existing.valid_to = effective_date
        existing.is_current = False
        change_type = 'UPDATE'
        new_snapshot = {k: unit_data.get(k) for k in checksum_fields}
    else:
        change_type = 'CREATE'
        new_snapshot = {k: unit_data.get(k) for k in checksum_fields}

    # Tạo bản ghi mới
    new_record_data = dict(unit_data)
    new_record_data['valid_from'] = effective_date
    new_record_data['valid_to'] = datetime(9999, 12, 31)
    new_record_data['is_current'] = True
    new_record_data['version_id'] = (existing.version_id + 1) if existing else 1
    new_record_data['predecessor_id'] = existing.row_id if existing else None

    new_record = Model(**{k: v for k, v in new_record_data.items() if hasattr(Model, k)})
    db.add(new_record)

    _write_sync_log(db, sync_source, level, unit_id, change_type, old_snapshot, new_snapshot, run_id)
    db.commit()

    return {
        'change_type': change_type,
        'unit_id': unit_id,
        'old_version': old_snapshot,
        'new_version': new_snapshot,
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

    Returns:
        Một bản ghi (nếu at có giá trị) hoặc list (nếu at=None)
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
    else:
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
    summary = {
        'run_id': run_id,
        'total': len(logs),
        'CREATE': 0,
        'UPDATE': 0,
        'NO_CHANGE': 0,
        'by_level': {},
    }
    for log in logs:
        ct = log.change_type or 'UNKNOWN'
        summary[ct] = summary.get(ct, 0) + 1
        lvl = log.level or 'unknown'
        if lvl not in summary['by_level']:
            summary['by_level'][lvl] = {'CREATE': 0, 'UPDATE': 0, 'NO_CHANGE': 0}
        summary['by_level'][lvl][ct] = summary['by_level'][lvl].get(ct, 0) + 1
    return summary
