"""
Crawl Typesense → prq.ground_truth: tách khỏi database.py để dễ test và ghi log đồng bộ.
"""
from __future__ import annotations

import json
import logging
import uuid
import warnings
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

# requests phát RequestsDependencyWarning khi urllib3/chardet lệch range — không làm fail sync
warnings.filterwarnings("ignore", message=r".*doesn't match a supported version.*")

import requests
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Config
from app.core.database import (
    AdminUnitMapping,
    GroundTruth,
    SessionLocal,
    TypesenseGroundTruthSyncRun,
)

logger = logging.getLogger(__name__)

# Join mat.*.old_id: pre-reform snapshot (explicit old_* / lineage)
PRE_ADMIN_VERSION = 1
# Post-reform lineage after admin_unit_mapping (join mat with admin_version=2)
POST_ADMIN_VERSION = 2


def _load_mapping_map(session) -> Dict[Tuple[int, int], int]:
    """(level, old_id) -> new_id; admin_version tăng dần, bản ghi sau ghi đè."""
    mappings = session.query(AdminUnitMapping).order_by(AdminUnitMapping.admin_version.asc()).all()
    return {(m.level, m.old_id): m.new_id for m in mappings}


def document_to_ground_truth_row(
    doc: Dict[str, Any],
    get_new_id: Callable[[int, Any], Optional[int]],
) -> Dict[str, Any]:
    """
    Map Typesense document → cột prq.ground_truth.

    - province_id / district_id / ward_id: áp dụng mat.admin_unit_mapping (post‑reform join tới mat với admin_version=2).
    - old_*: nếu document có field riêng, giữ nguyên (không map lại, tránh double mapping).
      Nếu thiếu, dùng raw ID từ khối chính **chưa** map.
    """
    raw_p = doc.get("province_id")
    raw_d = doc.get("district_id")
    raw_w = doc.get("ward_id")

    province_mapped = get_new_id(1, raw_p)
    district_mapped = get_new_id(2, raw_d)
    ward_mapped = get_new_id(3, raw_w)

    old_p = doc.get("old_province_id")
    old_d = doc.get("old_district_id")
    old_w = doc.get("old_ward_id")
    if old_p is None:
        old_p = raw_p
    if old_d is None:
        old_d = raw_d
    if old_w is None:
        old_w = raw_w

    location = doc.get("location") or []
    lat = location[0] if len(location) > 0 else None
    lon = location[1] if len(location) > 1 else None

    return {
        "id": int(doc.get("id")),
        "address": doc.get("address"),
        "old_address": doc.get("old_address"),
        "province_id": province_mapped,
        "district_id": district_mapped,
        "ward_id": ward_mapped,
        "old_province_id": old_p,
        "old_district_id": old_d,
        "old_ward_id": old_w,
        "old_address_eng": doc.get("old_address_eng"),
        "address_eng": doc.get("address_eng"),
        "latitude": lat,
        "longitude": lon,
        "popular": doc.get("popular", 0),
        "source_system": "TYPESENSE",
        "is_validated": False,
    }


def _build_upsert_stmt(db_records: List[Dict[str, Any]]):
    stmt = insert(GroundTruth).values(db_records)
    keys: set = set()
    for r in db_records:
        keys.update(r.keys())
    keys.discard("id")
    keys.discard("created_at")
    set_ = {k: getattr(stmt.excluded, k) for k in sorted(keys)}
    set_["updated_at"] = func.now()
    return stmt.on_conflict_do_update(index_elements=["id"], set_=set_)


def _export_url() -> str:
    return (
        f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}"
        f"/collections/{Config.TYPESENSE_COLLECTION}/documents/export"
    )


def _try_export_http_error(response: requests.Response) -> Optional[str]:
    """Đọc text lỗi nếu response không streamed / chưa consume body."""
    try:
        return response.text
    except Exception:  # noqa: BLE001 — stream edge cases
        return None


def sync_typesense_to_db(province_id: Optional[int] = None, limit: Optional[int] = None) -> int:
    """
    Crawl data từ Typesense và upsert vào prq.ground_truth.

    Dùng **GET /collections/{collection}/documents/export** (JSONL, streaming) — không qua máy search/scoring,
    nhẹ CPU hơn so với /documents/search phân trang.

    filter_by province_id được thử phía Typesense khi có; nếu field chưa index filter thì báo và export full,
    lọc province cục bộ (đồng nghĩa quét full stream một lần).

    Ghi nhận đợt sync vào ath.typesense_ground_truth_sync_run (commit ngay) và cập nhật
    last_sync_run_id / last_seen_at khi các cột đã tồn tại (migration SQL).

    Returns:
        Số document đã xử lý thành row (sau filter).
    """
    export_url = _export_url()
    headers = {"X-TYPESENSE-API-KEY": Config.TYPESENSE_API_KEY}

    batch_size_pg = 250
    batch_size_ts = int(getattr(Config, "TYPESENSE_EXPORT_REMOTE_BATCH_SIZE", None) or 250)

    print(f"Starting sync from Typesense collection: {Config.TYPESENSE_COLLECTION} (export JSONL)")
    logger.info("Typesense sync started collection=%s mode=export", Config.TYPESENSE_COLLECTION)

    total_processed = 0
    total_lines_scanned = 0
    total_upserted = 0
    db_records: List[Dict[str, Any]] = []

    session = SessionLocal()
    run_id: Optional[int] = None

    try:
        map_dict = _load_mapping_map(session)
        print("Loading Admin Unit Mapping for ID transformation...")

        def get_new_id(level: int, old_id: Any) -> Optional[int]:
            if old_id is None:
                return None
            return map_dict.get((level, old_id), old_id)

        run_row = TypesenseGroundTruthSyncRun(
            collection=Config.TYPESENSE_COLLECTION,
            filter_province_id=province_id,
            notes=f"sync_typesense_to_db_export {uuid.uuid4().hex[:8]}",
        )
        session.add(run_row)
        session.commit()
        run_id = run_row.id

        now = datetime.now(timezone.utc)

        def flush_batch() -> None:
            nonlocal total_upserted, db_records
            if not db_records:
                return
            stmt = _build_upsert_stmt(db_records)
            session.execute(stmt)
            session.commit()
            total_upserted += len(db_records)
            db_records = []

        connect_to = getattr(Config, "TYPESENSE_EXPORT_CONNECT_TIMEOUT_SEC", 60)
        read_to = getattr(Config, "TYPESENSE_EXPORT_READ_TIMEOUT_SEC", None)
        timeout = (connect_to, read_to)

        progress_every = int(getattr(Config, "TYPESENSE_EXPORT_PROGRESS_LINES", None) or 50_000)

        use_server_province_filter = province_id is not None
        stream_finished = False

        while not stream_finished:
            params: Dict[str, Any] = {"batch_size": batch_size_ts}
            if use_server_province_filter:
                params["filter_by"] = f"province_id:={province_id}"

            resp = requests.get(export_url, headers=headers, params=params, stream=True, timeout=timeout)

            if resp.status_code == 400:
                raw_txt = resp.text or "(no body)"
                txt = raw_txt.lower()
                resp.close()
                if use_server_province_filter and (
                    "non-indexed" in txt or "not a filterable" in txt
                ):
                    print(
                        "Note: 'province_id' is not filterable on export for this collection "
                        "(enable filter/facet on province_id in Typesense schema for server-side filter_by). "
                        "Exporting full collection and filtering locally."
                    )
                    logger.info(
                        "Typesense export: server filter_by rejected; retrying export without province filter"
                    )
                    use_server_province_filter = False
                    continue

                logger.error("Typesense export HTTP 400: %s", raw_txt)
                print(f"Error Typesense export: {raw_txt}")
                break

            if resp.status_code != 200:
                err = _try_export_http_error(resp) or "(no body)"
                resp.close()
                logger.error("Typesense export HTTP %s: %s", resp.status_code, err)
                print(f"Error Typesense export: {err}")
                break

            try:
                for raw in resp.iter_lines(decode_unicode=True):
                    if limit is not None and total_processed >= limit:
                        break

                    if not raw or not str(raw).strip():
                        continue

                    total_lines_scanned += 1
                    if total_lines_scanned % progress_every == 0:
                        print(
                            f"Export stream: {total_lines_scanned} JSON lines, "
                            f"{total_processed} rows accepted (batching to DB)..."
                        )
                        logger.info(
                            "Export progress json_lines=%s accepted_rows=%s",
                            total_lines_scanned,
                            total_processed,
                        )

                    try:
                        doc = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        logger.warning("Skipping bad JSON line: %s", exc)
                        continue

                    doc_old_province_id = doc.get("province_id")
                    if province_id is not None and doc_old_province_id != province_id:
                        continue

                    if limit is not None and total_processed >= limit:
                        break

                    try:
                        row = document_to_ground_truth_row(doc, get_new_id)
                    except (TypeError, ValueError) as exc:
                        logger.warning("Skipping document id=%s: %s", doc.get("id"), exc)
                        continue

                    row["last_sync_run_id"] = run_id
                    row["last_seen_at"] = now
                    db_records.append(row)
                    total_processed += 1

                    if len(db_records) >= batch_size_pg:
                        flush_batch()
            finally:
                resp.close()

            stream_finished = True

        flush_batch()

        if run_id is not None:
            run_final = session.get(TypesenseGroundTruthSyncRun, run_id)
            if run_final:
                run_final.finished_at = datetime.now(timezone.utc)
                run_final.records_scanned = total_lines_scanned
                run_final.records_upserted = total_upserted
                session.commit()

        print(f"Sync completed. Total rows upsert-ready: {total_processed} (lines from export: {total_lines_scanned})")
        logger.info(
            "Typesense export sync done processed=%s rows_committed_batches=%s lines_scanned=%s",
            total_processed,
            total_upserted,
            total_lines_scanned,
        )
        return total_processed

    except Exception as e:
        logger.exception("Error during Typesense sync: %s", e)
        print(f"Error during sync: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()


def get_admin_version_constants() -> Tuple[int, int]:
    return PRE_ADMIN_VERSION, POST_ADMIN_VERSION
