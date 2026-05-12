#!/usr/bin/env python3
"""
Migration script: Cập nhật address_cleansing_queue từ admin_version=1 sang admin_version=2

Chức năng:
1. Tạo mapping table từ admin v1 sang v2 dựa trên tên tương ứng  
2. Cập nhật province_id, district_id, ward_id trong address_cleansing_queue
3. Validate dữ liệu sau khi migration
4. Tạo backup bảng trước khi migration

Mapping v1↔v2 chỉ lấy bản ghi mat.* có is_deleted = FALSE (hoặc NULL).
Trước đây lọc v1 với is_deleted = TRUE — nhiều DB không dùng quy ước đó → mapping rỗng.

Ưu tiên cập nhật từ `mat.ward_mapping` (theo lineage: `old_ward_id` -> wl v1 `ward_id` = `ward_id_old`),
sau đó mới fallback `temp.admin_v1_v2_mapping` theo tên.

Ghép queue ↔ master theo lineage (khóa chuẩn): `old_province_id/old_district_id/old_ward_id`
= `mat.*.old_id` với `admin_version = 1` (`app.domain.acq_mat_lineage`). APPLY và coverage
mapping dựa trên khóa v1 suy ra từ lineage đó — không ghép mapping trực tiếp vào acq.*_id cũ khi lineage có giá trị.

Usage:
    python scripts/migration/migrate_acq_to_admin_v2.py --validate-only
    python scripts/migration/migrate_acq_to_admin_v2.py --create-mapping-only
    python scripts/migration/migrate_acq_to_admin_v2.py --migrate
    python scripts/migration/migrate_acq_to_admin_v2.py --migrate --backup
    python scripts/migration/migrate_acq_to_admin_v2.py --migrate --dry-run

Logs dùng flush=True từng dòng; mapping tách transaction commit sau province/district/ward INSERT.
Tuỳ máy có thể thêm: set PYTHONUNBUFFERED=1
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.db_connector import DBConnector
from app.ai.utils.config_loader import load_config_with_env
from app.domain.acq_mat_lineage import sql_count_queue_rows_full_lineage_v1_resolution


def _configure_stdout_utf8() -> None:
    """Tránh UnicodeEncodeError (cp1252) khi log tiếng Việt trên Windows."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _log(msg: str = "") -> None:
    """Stdout flush; fallback UTF-8 bytes nếu console không nhận Unicode."""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        except Exception:
            print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)


# Active v1 master by business id (matches lineage constants for UPDATE … JOIN mat.* pl/dl/wl)
_WHERE_PROVINCE_V1_MASTER = (
    "pl.admin_version = 1 AND COALESCE(pl.is_deleted, FALSE) = FALSE "
    "AND COALESCE(pl.is_active, TRUE) = TRUE"
)
_WHERE_DISTRICT_V1_MASTER = (
    "dl.admin_version = 1 AND COALESCE(dl.is_deleted, FALSE) = FALSE "
    "AND COALESCE(dl.is_active, TRUE) = TRUE"
)
_WHERE_WARD_V1_MASTER = (
    "wl.admin_version = 1 AND COALESCE(wl.is_deleted, FALSE) = FALSE "
    "AND COALESCE(wl.is_active, TRUE) = TRUE"
)


def print_mat_v1_duplicate_old_id_smoke(db) -> None:
    """Số khóa old_id trùng trên mat.* (admin_version=1); kỳ vọng 0 sau chuẩn hóa master."""
    sql = """
            SELECT 'province'::text AS rel,
                   (SELECT COUNT(*) FROM (
                     SELECT old_id FROM mat.province WHERE admin_version = 1 AND old_id IS NOT NULL
                     GROUP BY old_id HAVING COUNT(*) > 1
                   ) t)::bigint AS duplicate_old_id_keys
            UNION ALL
            SELECT 'district',
                   (SELECT COUNT(*) FROM (
                     SELECT old_id FROM mat.district WHERE admin_version = 1 AND old_id IS NOT NULL
                     GROUP BY old_id HAVING COUNT(*) > 1
                   ) t)::bigint
            UNION ALL
            SELECT 'ward',
                   (SELECT COUNT(*) FROM (
                     SELECT old_id FROM mat.ward WHERE admin_version = 1 AND old_id IS NOT NULL
                     GROUP BY old_id HAVING COUNT(*) > 1
                   ) t)::bigint
            """
    _log("   mat v1 duplicate old_id keys (expect 0):")
    with db.cursor() as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            _log(f"     {row['rel']:<8}: {row['duplicate_old_id_keys']}")


def count_queue_rows_ward_mapping_lineage(db):
    """Queue rows có ít nhất một mapping ward_mapping hợp lệ qua lineage wl."""
    with db.cursor() as cur:
        cur.execute(
            """
            WITH per_acq AS (
              SELECT acq.id,
                     bool_or(
                       wm.ward_id_new IS NOT NULL
                       AND COALESCE(wm.is_deleted, FALSE) = FALSE
                     ) AS has_wm
              FROM prq.address_cleansing_queue acq
              INNER JOIN mat.ward wl ON acq.old_ward_id IS NOT DISTINCT FROM wl.old_id
                AND """
            + _WHERE_WARD_V1_MASTER
            + """
              LEFT JOIN mat.ward_mapping wm ON wm.ward_id_old = wl.ward_id
              WHERE acq.old_ward_id IS NOT NULL
              GROUP BY acq.id
            )
            SELECT COUNT(*)::bigint AS queue_with_old_ward,
                   COUNT(*) FILTER (WHERE has_wm)::bigint AS updatable_via_ward_mapping
            FROM per_acq
            """
        )
        return cur.fetchone()


def apply_ward_mapping_lineage_updates(db, dry_run: bool = False) -> int:
    """
    Cập nhật denorm P/D/W + tên từ mat (v2) theo mat.ward_mapping, khóa lineage v1.
    Trả về số hàng queue đã UPDATE (hoặc 0 nếu dry_run).
    """
    _log(
        "   [ward_mapping] "
        + ("COUNT eligible rows (dry-run)..." if dry_run else "Applying UPDATE from mat.ward_mapping...")
    )
    subq = (
        """
        SELECT acq2.id AS acq_row_id,
               COALESCE(wm.province_id_new, dn.province_id) AS res_province_id,
               COALESCE(wm.district_id_new, wn.district_id) AS res_district_id,
               wm.ward_id_new AS res_ward_id,
               pn.province_name AS res_province_name,
               dn.district_name AS res_district_name,
               wn.ward_name AS res_ward_name
        FROM prq.address_cleansing_queue acq2
        INNER JOIN mat.ward wl
          ON acq2.old_ward_id IS NOT DISTINCT FROM wl.old_id
          AND """
        + _WHERE_WARD_V1_MASTER
        + """
        INNER JOIN LATERAL (
          SELECT *
          FROM mat.ward_mapping wm0
          WHERE wm0.ward_id_old = wl.ward_id
            AND COALESCE(wm0.is_deleted, FALSE) = FALSE
            AND wm0.ward_id_new IS NOT NULL
          ORDER BY wm0.effective_date_from DESC NULLS LAST, wm0.ward_mapping_id DESC
          LIMIT 1
        ) wm ON TRUE
        INNER JOIN mat.ward wn
          ON wn.ward_id = wm.ward_id_new
          AND wn.admin_version = 2
          AND COALESCE(wn.is_deleted, FALSE) = FALSE
          AND COALESCE(wn.is_active, TRUE) = TRUE
        LEFT JOIN mat.district dn
          ON dn.district_id = COALESCE(wm.district_id_new, wn.district_id)
          AND dn.admin_version = 2
          AND COALESCE(dn.is_deleted, FALSE) = FALSE
          AND COALESCE(dn.is_active, TRUE) = TRUE
        LEFT JOIN mat.province pn
          ON pn.province_id = COALESCE(wm.province_id_new, dn.province_id)
          AND pn.admin_version = 2
          AND COALESCE(pn.is_deleted, FALSE) = FALSE
          AND COALESCE(pn.is_active, TRUE) = TRUE
        """
    )

    if dry_run:
        with db.cursor() as cur:
            cur.execute(f"SELECT COUNT(*)::bigint AS n FROM ({subq}) q")
            n = cur.fetchone()["n"]
        _log(f"   [dry-run] Rows match ward_mapping (lineage): {int(n):,}")
        return 0

    upd = (
        """
        UPDATE prq.address_cleansing_queue acq
        SET province_id = x.res_province_id,
            district_id = x.res_district_id,
            ward_id = x.res_ward_id,
            province_name = x.res_province_name,
            district_name = x.res_district_name,
            ward_name = x.res_ward_name
        FROM ("""
        + subq
        + ") AS x\n        WHERE acq.id = x.acq_row_id"
    )
    with db.cursor() as cur:
        cur.execute(upd)
        n = cur.rowcount
    _log(f"   Updated {n:,} queue rows via mat.ward_mapping (lineage v1 -> v2)")
    return n


def create_backup_table(db):
    """Tạo backup bảng address_cleansing_queue"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_table = f"address_cleansing_queue_backup_{timestamp}"
    
    _log(f"Creating backup table: prq.{backup_table}")

    with db.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE prq.{backup_table} AS 
            SELECT * FROM prq.address_cleansing_queue
        """)
        
        # Check backup count
        cur.execute(f"SELECT COUNT(*) as count FROM prq.{backup_table}")
        backup_count = cur.fetchone()['count']
        _log(f"   Backup created with {backup_count:,} records")

    return backup_table


def create_admin_mapping_table(db):
    """Tạo bảng mapping giữa admin v1 và v2 dựa trên tên.

    Mỗi INSERT trong một ``with db.cursor()`` riêng để commit sớm và log không bị treo một chunk dài.
    """

    _log("[migrate] Step 1/6: DROP + CREATE temp.admin_v1_v2_mapping ...")
    with db.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS temp.admin_v1_v2_mapping")
        cur.execute("CREATE SCHEMA IF NOT EXISTS temp")
        cur.execute(
            """
            CREATE TABLE temp.admin_v1_v2_mapping (
                level VARCHAR(10) NOT NULL,
                v1_id INTEGER NOT NULL,
                v1_name VARCHAR(200),
                v2_id INTEGER,
                v2_name VARCHAR(200),
                match_type VARCHAR(20),
                confidence FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
    _log("[migrate] Step 1/6: OK (committed).")

    _log("[migrate] Step 2/6: INSERT province v1->v2 (name match). Chạy có thể vài giây...")
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO temp.admin_v1_v2_mapping (level, v1_id, v1_name, v2_id, v2_name, match_type)
            SELECT
                'province' as level,
                p1.province_id as v1_id,
                p1.province_name as v1_name,
                p2.province_id as v2_id,
                p2.province_name as v2_name,
                'exact' as match_type
            FROM mat.province p1
            JOIN mat.province p2 ON (
                p1.admin_version = 1 AND p2.admin_version = 2 AND
                (
                    LOWER(TRIM(p1.province_name)) = LOWER(TRIM(p2.province_name))
                    OR (p1.province_name ILIKE '%Ho Chi Minh%' AND p2.province_name ILIKE '%Ho Chi Minh%')
                    OR (p1.province_name ILIKE '%Ha Noi%' AND p2.province_name ILIKE '%Ha Noi%')
                    OR (p1.province_name ILIKE '%Da Nang%' AND p2.province_name ILIKE '%Da Nang%')
                    OR (p1.province_name ILIKE '%Hai Phong%' AND p2.province_name ILIKE '%Hai Phong%')
                    OR (p1.province_name ILIKE '%Can Tho%' AND p2.province_name ILIKE '%Can Tho%')
                )
            )
            WHERE COALESCE(p1.is_deleted, FALSE) = FALSE
              AND COALESCE(p2.is_deleted, FALSE) = FALSE
            """
        )
        rc = cur.rowcount
    _log(f"[migrate] Step 2/6: OK (committed). INSERT rowcount={rc:,}")

    _log("[migrate] Step 3/6: INSERT district v1->v2 (depends on province mapping). Có thể lâu hơn...")
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO temp.admin_v1_v2_mapping (level, v1_id, v1_name, v2_id, v2_name, match_type)
            SELECT
                'district' as level,
                d1.district_id as v1_id,
                d1.district_name as v1_name,
                d2.district_id as v2_id,
                d2.district_name as v2_name,
                'exact' as match_type
            FROM mat.district d1
            JOIN mat.district d2 ON (
                d1.admin_version = 1 AND d2.admin_version = 2 AND
                LOWER(TRIM(d1.district_name)) = LOWER(TRIM(d2.district_name)) AND
                EXISTS (
                    SELECT 1 FROM temp.admin_v1_v2_mapping pm
                    WHERE pm.level = 'province'
                    AND pm.v1_id = d1.province_id
                    AND pm.v2_id = d2.province_id
                )
            )
            WHERE COALESCE(d1.is_deleted, FALSE) = FALSE
              AND COALESCE(d2.is_deleted, FALSE) = FALSE
            """
        )
        rc = cur.rowcount
    _log(f"[migrate] Step 3/6: OK (committed). INSERT rowcount={rc:,}")

    _log("[migrate] Step 4/6: INSERT ward v1->v2 (depends on district mapping). Thường là bước nặng nhất...")
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO temp.admin_v1_v2_mapping (level, v1_id, v1_name, v2_id, v2_name, match_type)
            SELECT
                'ward' as level,
                w1.ward_id as v1_id,
                w1.ward_name as v1_name,
                w2.ward_id as v2_id,
                w2.ward_name as v2_name,
                'exact' as match_type
            FROM mat.ward w1
            JOIN mat.ward w2 ON (
                w1.admin_version = 1 AND w2.admin_version = 2 AND
                LOWER(TRIM(w1.ward_name)) = LOWER(TRIM(w2.ward_name)) AND
                EXISTS (
                    SELECT 1 FROM temp.admin_v1_v2_mapping dm
                    WHERE dm.level = 'district'
                    AND dm.v1_id = w1.district_id
                    AND dm.v2_id = w2.district_id
                )
            )
            WHERE COALESCE(w1.is_deleted, FALSE) = FALSE
              AND COALESCE(w2.is_deleted, FALSE) = FALSE
            """
        )
        rc = cur.rowcount
    _log(f"[migrate] Step 4/6: OK (committed). INSERT rowcount={rc:,}")

    _log("[migrate] Step 5/6: Mapping statistics by level...")
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT level, COUNT(*) as mapping_count
            FROM temp.admin_v1_v2_mapping
            GROUP BY level
            ORDER BY level
            """
        )
        results = cur.fetchall()

    _log("   Mapping statistics:")
    for r in results:
        _log(f"     {r['level']:<10}: {r['mapping_count']:,} mappings")
    _log("[migrate] Step 5/6: OK.")
    _log("[migrate] Step 6/6: temp.admin_v1_v2_mapping ready.")

    return True

def validate_mapping_coverage(db):
    """Coverage của temp.admin_v1_v2_mapping theo lineage v1 (old_* ↔ mat.old_id, admin_version=1)."""

    _log("[migrate] Coverage: temp.admin_v1_v2_mapping vs lineage v1 keys (truy vấn queue + mat)...")

    checks = (
        (
            "province",
            (
                """
            SELECT COUNT(DISTINCT pl.province_id) AS total_used,
                   COUNT(DISTINCT CASE WHEN m.v2_id IS NOT NULL THEN pl.province_id END) AS mapped_count,
                   ROUND(
                       COUNT(DISTINCT CASE WHEN m.v2_id IS NOT NULL THEN pl.province_id END) * 100.0
                       / NULLIF(COUNT(DISTINCT pl.province_id), 0), 2
                   ) AS coverage_percent
            FROM prq.address_cleansing_queue acq
            JOIN mat.province pl ON acq.old_province_id = pl.old_id AND """
                + _WHERE_PROVINCE_V1_MASTER
                + """
            LEFT JOIN temp.admin_v1_v2_mapping m
              ON m.level = 'province' AND m.v1_id = pl.province_id
            WHERE acq.old_province_id IS NOT NULL
            """
            ),
        ),
        (
            "district",
            (
                """
            SELECT COUNT(DISTINCT dl.district_id) AS total_used,
                   COUNT(DISTINCT CASE WHEN m.v2_id IS NOT NULL THEN dl.district_id END) AS mapped_count,
                   ROUND(
                       COUNT(DISTINCT CASE WHEN m.v2_id IS NOT NULL THEN dl.district_id END) * 100.0
                       / NULLIF(COUNT(DISTINCT dl.district_id), 0), 2
                   ) AS coverage_percent
            FROM prq.address_cleansing_queue acq
            JOIN mat.district dl ON acq.old_district_id = dl.old_id AND """
                + _WHERE_DISTRICT_V1_MASTER
                + """
            LEFT JOIN temp.admin_v1_v2_mapping m
              ON m.level = 'district' AND m.v1_id = dl.district_id
            WHERE acq.old_district_id IS NOT NULL
            """
            ),
        ),
        (
            "ward",
            (
                """
            SELECT COUNT(DISTINCT wl.ward_id) AS total_used,
                   COUNT(DISTINCT CASE WHEN m.v2_id IS NOT NULL THEN wl.ward_id END) AS mapped_count,
                   ROUND(
                       COUNT(DISTINCT CASE WHEN m.v2_id IS NOT NULL THEN wl.ward_id END) * 100.0
                       / NULLIF(COUNT(DISTINCT wl.ward_id), 0), 2
                   ) AS coverage_percent
            FROM prq.address_cleansing_queue acq
            JOIN mat.ward wl ON acq.old_ward_id = wl.old_id AND """
                + _WHERE_WARD_V1_MASTER
                + """
            LEFT JOIN temp.admin_v1_v2_mapping m
              ON m.level = 'ward' AND m.v1_id = wl.ward_id
            WHERE acq.old_ward_id IS NOT NULL
            """
            ),
        ),
    )

    with db.cursor() as cur:
        for level, sql in checks:
            _log(f"   Running coverage query: {level} ...")
            cur.execute(sql)
            result = cur.fetchone()
            _log(
                f"   {level.capitalize():<10}: {result['mapped_count']:,}/{result['total_used']:,}"
                f" ({result['coverage_percent']}%)"
            )

    return True

def migrate_address_cleansing_queue(db, dry_run=False):
    """Migration chính: ward_mapping (ưu tiên) rồi temp.admin_v1_v2_mapping theo lineage."""

    _log(f"{'[DRY RUN] ' if dry_run else ''}Migrating address_cleansing_queue to admin_version=2...")

    _log("   Counting ward_mapping coverage via lineage (GROUP BY acq.id)...")
    wm = count_queue_rows_ward_mapping_lineage(db)
    qow = int(wm["queue_with_old_ward"] or 0)
    uwm = int(wm["updatable_via_ward_mapping"] or 0)
    pct_wm = round(100.0 * uwm / qow, 2) if qow else 0.0
    _log(
        "   ward_mapping (lineage v1 ward_id): "
        f"rows with non-null old_ward={qow:,}; with mapping={uwm:,} ({pct_wm}%)"
    )

    apply_ward_mapping_lineage_updates(db, dry_run=dry_run)

    _log("   Running expanded / dedup stats (LEFT JOIN lineage + temp mapping)...")
    expanded_sql = (
        """
            WITH expanded AS (
              SELECT acq.id,
                     pm.v2_id AS pm_v2,
                     dm.v2_id AS dm_v2,
                     wm.v2_id AS wm_v2
              FROM prq.address_cleansing_queue acq
              LEFT JOIN mat.province pl
                ON acq.old_province_id = pl.old_id AND """
        + _WHERE_PROVINCE_V1_MASTER
        + """
              LEFT JOIN mat.district dl
                ON acq.old_district_id = dl.old_id AND """
        + _WHERE_DISTRICT_V1_MASTER
        + """
              LEFT JOIN mat.ward wl
                ON acq.old_ward_id = wl.old_id AND """
        + _WHERE_WARD_V1_MASTER
        + """
              LEFT JOIN temp.admin_v1_v2_mapping pm
                ON pm.level = 'province' AND pm.v1_id = pl.province_id
              LEFT JOIN temp.admin_v1_v2_mapping dm
                ON dm.level = 'district' AND dm.v1_id = dl.district_id
              LEFT JOIN temp.admin_v1_v2_mapping wm
                ON wm.level = 'ward' AND wm.v1_id = wl.ward_id
            ),
            dedup AS (
              SELECT id,
                     bool_or(pm_v2 IS NOT NULL) AS prov_ok,
                     bool_or(dm_v2 IS NOT NULL) AS dist_ok,
                     bool_or(wm_v2 IS NOT NULL) AS ward_ok
              FROM expanded
              GROUP BY id
            )
            SELECT
              COUNT(*)::bigint AS total,
              COUNT(*) FILTER (WHERE prov_ok)::bigint AS province_mappable,
              COUNT(*) FILTER (WHERE dist_ok)::bigint AS district_mappable,
              COUNT(*) FILTER (WHERE ward_ok)::bigint AS ward_mappable
            FROM dedup
        """
    )

    with db.cursor() as cur:
        cur.execute(expanded_sql)

        stats = cur.fetchone()
        _log("   Records analysis (name-based temp mapping still available after ward_mapping):")
        _log(f"     Total records: {stats['total']:,}")
        _log(f"     Province mappable: {stats['province_mappable']:,}")
        _log(f"     District mappable: {stats['district_mappable']:,}")
        _log(f"     Ward mappable: {stats['ward_mappable']:,}")

        if not dry_run:
            _log("   Updating province_id (temp mapping via lineage)...")
            cur.execute(
                """
                UPDATE prq.address_cleansing_queue acq
                SET province_id = pm.v2_id,
                    province_name = pm.v2_name
                FROM temp.admin_v1_v2_mapping pm
                INNER JOIN mat.province pl
                  ON pl.province_id = pm.v1_id AND """
                + _WHERE_PROVINCE_V1_MASTER
                + """
                WHERE pm.level = 'province'
                  AND acq.old_province_id IS NOT DISTINCT FROM pl.old_id
            """
            )
            province_updated = cur.rowcount
            _log(f"     Updated {province_updated:,} province references")

            _log("   Updating district_id (temp mapping via lineage)...")
            cur.execute(
                """
                UPDATE prq.address_cleansing_queue acq
                SET district_id = dm.v2_id,
                    district_name = dm.v2_name
                FROM temp.admin_v1_v2_mapping dm
                INNER JOIN mat.district dl
                  ON dl.district_id = dm.v1_id AND """
                + _WHERE_DISTRICT_V1_MASTER
                + """
                WHERE dm.level = 'district'
                  AND acq.old_district_id IS NOT DISTINCT FROM dl.old_id
            """
            )
            district_updated = cur.rowcount
            _log(f"     Updated {district_updated:,} district references")

            _log("   Updating ward_id (temp mapping via lineage)...")
            cur.execute(
                """
                UPDATE prq.address_cleansing_queue acq
                SET ward_id = wm.v2_id,
                    ward_name = wm.v2_name
                FROM temp.admin_v1_v2_mapping wm
                INNER JOIN mat.ward wl
                  ON wl.ward_id = wm.v1_id AND """
                + _WHERE_WARD_V1_MASTER
                + """
                WHERE wm.level = 'ward'
                  AND acq.old_ward_id IS NOT DISTINCT FROM wl.old_id
            """
            )
            ward_updated = cur.rowcount
            _log(f"     Updated {ward_updated:,} ward references")
        else:
            _log("   [DRY RUN] Skipping UPDATE statements (province/district/ward).")

    return True

def validate_migration_result(db):
    """Validate lineage quality + đọc FK denormalised so với mat (snapshot sau migrate)."""

    _log("Validating migration results (read-only)...")

    with db.cursor() as cur:
        cur.execute(sql_count_queue_rows_full_lineage_v1_resolution())
        triple = cur.fetchone()
        n = triple.get("queue_rows_matching_lineage_triple_v1_master")
        _log(f"   Rows matching lineage triple INNER join (canonical): {int(n):,}")

        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE old_province_id IS NULL) AS null_old_province,
                COUNT(*) FILTER (WHERE old_district_id IS NULL) AS null_old_district,
                COUNT(*) FILTER (WHERE old_ward_id IS NULL) AS null_old_ward
            FROM prq.address_cleansing_queue
        """)
        nulls = cur.fetchone()
        _log(
            f"   Queue NULL lineage keys | old_province: {nulls['null_old_province']:,} | "
            f"old_district: {nulls['null_old_district']:,} | old_ward: {nulls['null_old_ward']:,}"
        )

        _log(
            "   Denormalised FK join (queue ids -> mat.*): use COUNT(DISTINCT acq.id) so rows are "
            "not multiplied when the same business id exists under multiple admin_version rows."
        )
        cur.execute("""
            SELECT 
                'Province' as level,
                p.admin_version,
                COUNT(DISTINCT acq.id) as count
            FROM prq.address_cleansing_queue acq
            JOIN mat.province p ON acq.province_id = p.province_id
              AND COALESCE(p.is_deleted, FALSE) = FALSE
            GROUP BY p.admin_version
            UNION ALL
            SELECT 
                'District' as level,
                d.admin_version,
                COUNT(DISTINCT acq.id) as count
            FROM prq.address_cleansing_queue acq
            JOIN mat.district d ON acq.district_id = d.district_id
              AND COALESCE(d.is_deleted, FALSE) = FALSE
            GROUP BY d.admin_version
            UNION ALL
            SELECT 
                'Ward' as level,
                w.admin_version,
                COUNT(DISTINCT acq.id) as count
            FROM prq.address_cleansing_queue acq
            JOIN mat.ward w ON acq.ward_id = w.ward_id
              AND COALESCE(w.is_deleted, FALSE) = FALSE
            GROUP BY w.admin_version
            ORDER BY level, admin_version
        """)
        
        results = cur.fetchall()
        _log("   Admin version histogram (distinct queue rows per mat.admin_version match):")
        for r in results:
            level = r['level']
            version = r['admin_version']
            count = r['count']
            _log(f"     {level:<10} admin_version={version}: {count:,}")

    return True

def main():
    _configure_stdout_utf8()
    parser = argparse.ArgumentParser(description='Migrate address_cleansing_queue to admin_version=2')
    parser.add_argument('--validate-only', action='store_true', help='Only validate current state')
    parser.add_argument('--create-mapping-only', action='store_true', help='Only create mapping table')
    parser.add_argument('--migrate', action='store_true', help='Run full migration')
    parser.add_argument('--backup', action='store_true', help='Create backup before migration')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without actual updates')
    
    args = parser.parse_args()
    
    try:
        _log(f"Starting admin_version migration - {datetime.now()}")
        _log("Loading config (app/ai/config.yaml + env)...")
        cfg = load_config_with_env('app/ai/config.yaml')
        db = DBConnector(cfg['database'])
        _log(
            f"Connecting to PostgreSQL {cfg['database'].get('host')}:{cfg['database'].get('port')}/"
            f"{cfg['database'].get('dbname')} ..."
        )
        db.connect()
        _log("Connected.")

        if args.validate_only:
            _log("VALIDATE-ONLY mode")
            print_mat_v1_duplicate_old_id_smoke(db)
            validate_migration_result(db)

        elif args.create_mapping_only:
            _log("CREATE-MAPPING-ONLY mode")
            create_admin_mapping_table(db)
            validate_mapping_coverage(db)

        elif args.migrate:
            _log(
                "FULL MIGRATION mode"
                + (" [DRY RUN: no queue UPDATE]" if args.dry_run else "")
            )

            # Create backup if requested
            if args.backup:
                backup_table = create_backup_table(db)
                _log(f"   Backup created: prq.{backup_table}")

            # Create mapping
            create_admin_mapping_table(db)
            validate_mapping_coverage(db)

            # Run migration
            migrate_address_cleansing_queue(db, dry_run=args.dry_run)

            # Đọc lại snapshot sau luồng (dry-run: queue không đổi; vẫn hữu ích để xác nhận script chạy hết)
            if args.dry_run:
                _log("[DRY RUN] Post-check read-only (queue unchanged):")
            print_mat_v1_duplicate_old_id_smoke(db)
            validate_migration_result(db)

        else:
            parser.print_help()

        db.disconnect()
        _log(f"\nMigration completed successfully - {datetime.now()}")

    except Exception as e:
        try:
            print(f"Migration failed: {e}", flush=True)
        except UnicodeEncodeError:
            _log(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()