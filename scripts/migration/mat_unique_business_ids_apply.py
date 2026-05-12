"""
Tạo UNIQUE partial index trên mã nghiệp vụ mat.* (chỉ khi is_deleted = false).

Chạy SAU:
  - scripts/migration/20260512_mat_is_active_drop_is_current.sql
  - scripts/migration/20260512_mat_remap_duplicate_business_ids.sql (remap *_id, không xóa)
  - và khi không còn trùng business id với is_deleted = false.

CREATE INDEX CONCURRENTLY không chạy trong transaction — script dùng autocommit.

Usage:
  python scripts/migration/mat_unique_business_ids_apply.py --check-only
  python scripts/migration/mat_unique_business_ids_apply.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


def _url() -> str:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    user = os.getenv("DB_USER")
    pwd = quote_plus(os.getenv("DB_PASS") or "")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT") or "5432"
    name = os.getenv("DB_NAME")
    if not all([user, host, name]) or not os.getenv("DB_PASS"):
        raise SystemExit("Missing DB_* in .env")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


_DUP_SQL = {
    "province": """
        SELECT province_id, COUNT(*) AS n
        FROM mat.province
        WHERE is_deleted = FALSE
        GROUP BY province_id
        HAVING COUNT(*) > 1
        ORDER BY n DESC, province_id
        LIMIT 50
    """,
    "district": """
        SELECT district_id, COUNT(*) AS n
        FROM mat.district
        WHERE is_deleted = FALSE
        GROUP BY district_id
        HAVING COUNT(*) > 1
        ORDER BY n DESC, district_id
        LIMIT 50
    """,
    "ward": """
        SELECT ward_id, COUNT(*) AS n
        FROM mat.ward
        WHERE is_deleted = FALSE
        GROUP BY ward_id
        HAVING COUNT(*) > 1
        ORDER BY n DESC, ward_id
        LIMIT 50
    """,
}

_INDEXES = [
    (
        "uq_mat_province_business_id_alive",
        "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_mat_province_business_id_alive "
        "ON mat.province (province_id) WHERE is_deleted = FALSE",
    ),
    (
        "uq_mat_district_business_id_alive",
        "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_mat_district_business_id_alive "
        "ON mat.district (district_id) WHERE is_deleted = FALSE",
    ),
    (
        "uq_mat_ward_business_id_alive",
        "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_mat_ward_business_id_alive "
        "ON mat.ward (ward_id) WHERE is_deleted = FALSE",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.check_only and not args.apply:
        parser.error("Chọn --check-only hoặc --apply")

    engine = create_engine(_url(), poolclass=NullPool, isolation_level="AUTOCOMMIT")

    bad = False
    with engine.connect() as conn:
        for label, sql in _DUP_SQL.items():
            rows = conn.execute(text(sql)).fetchall()
            if rows:
                bad = True
                print(f"[DUPLICATES] {label}: {len(rows)} group(s) shown (cap 50)")
                for r in rows:
                    print(f"  id={r[0]} count={r[1]}")

    if bad:
        print("\nResolve duplicate business keys before UNIQUE index. Exiting.")
        sys.exit(1)

    print("OK: no duplicate (province_id|district_id|ward_id) with is_deleted=false.")

    if args.check_only:
        return

    with engine.connect() as conn:
        for name, ddl in _INDEXES:
            print(f"Applying {name} ...")
            conn.execute(text(ddl))
            print(f"  done: {name}")

    print("CREATE UNIQUE INDEX CONCURRENTLY finished.")


if __name__ == "__main__":
    main()
