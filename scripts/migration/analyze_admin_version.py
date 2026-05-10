#!/usr/bin/env python3
"""
Analyze address_cleansing_queue vs mat.* using:
- Canonical lineage join (old_* = mat.old_id, admin_version = 1).
- Optional histogram for denormalised FK (acq.province_id / ...) — snapshot only.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.db_connector import DBConnector
from app.ai.utils.config_loader import load_config_with_env
from app.domain.acq_mat_lineage import sql_count_queue_rows_full_lineage_v1_resolution


def main():
    try:
        cfg = load_config_with_env("app/ai/config.yaml")
        db = DBConnector(cfg["database"])
        db.connect()

        print("=== ADDRESS_CLEANSING_QUEUE ===")
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM prq.address_cleansing_queue")
            total_count = cur.fetchone()["total"]
            print(f"Total rows: {total_count}")

            cur.execute(sql_count_queue_rows_full_lineage_v1_resolution())
            triple = cur.fetchone()
            n = triple.get("queue_rows_matching_lineage_triple_v1_master")
            print(f"Rows matching INNER lineage triple (canonical): {int(n):,}")

        print("\n=== ADMIN_VERSION histogram via denormalised FK (diagnostic snapshot) ===")
        with db.cursor() as cur:
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
            for r in results:
                print(f"{r['level']:<10} admin_version={r['admin_version']:<4} count={r['count']}")

        print("\n=== SAMPLE: names from lineage masters (v1 via old_* = old_id) ===")
        with db.cursor() as cur:
            cur.execute("""
                SELECT 
                    acq.id,
                    acq.raw_address,
                    p.province_name,
                    d.district_name,
                    w.ward_name
                FROM prq.address_cleansing_queue acq
                JOIN mat.province p ON acq.old_province_id = p.old_id AND p.admin_version = 1
                  AND COALESCE(p.is_deleted, FALSE) = FALSE AND COALESCE(p.is_current, TRUE) = TRUE
                JOIN mat.district d ON acq.old_district_id = d.old_id AND d.admin_version = 1
                  AND COALESCE(d.is_deleted, FALSE) = FALSE AND COALESCE(d.is_current, TRUE) = TRUE
                JOIN mat.ward w ON acq.old_ward_id = w.old_id AND w.admin_version = 1
                  AND COALESCE(w.is_deleted, FALSE) = FALSE AND COALESCE(w.is_current, TRUE) = TRUE
                LIMIT 5
            """)
            samples = cur.fetchall()
            for s in samples:
                print(f"\nid={s['id']}")
                print(f" raw={s['raw_address']}")
                print(f" lineage_v1_province/district/ward: {s['province_name']} / "
                      f"{s['district_name']} / {s['ward_name']}")

        print("\n=== mat.admin_unit_mapping (when present) ===")
        try:
            with db.cursor() as cur:
                cur.execute("SELECT COUNT(*) as total FROM mat.admin_unit_mapping")
                mc = cur.fetchone()["total"]
                print(f"Total mapping records: {mc}")
                if mc and int(mc) > 0:
                    cur.execute("""
                        SELECT level, admin_version, COUNT(*) as count
                        FROM mat.admin_unit_mapping
                        GROUP BY level, admin_version
                        ORDER BY level, admin_version
                    """)
                    for r in cur.fetchall():
                        print(
                            f" level={r['level']:<12} admin_version={r['admin_version']:<4} count={r['count']}"
                        )
        except Exception as inner:
            print(f"(skip admin_unit_mapping) {inner}")

        db.disconnect()
        print("\nDatabase analysis completed")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
