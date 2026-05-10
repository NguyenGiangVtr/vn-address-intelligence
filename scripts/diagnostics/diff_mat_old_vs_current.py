#!/usr/bin/env python3
"""
diff_mat_old_vs_current.py
==========================

Quick diagnostic: so sánh bảng `mat.<level>_old` (snapshot từ OLD_DB clone bằng
`scripts/migration/clone_old_mat_tables.py`) với master hiện tại `mat.<level>`
trên DB mới, nhằm xác định trường nào đã bị cập nhật khác đi.

Báo cáo:
1. Số bản ghi trong OLD vs CURRENT (theo admin_version nếu master có cột này).
2. ID xuất hiện ở OLD nhưng không ở CURRENT (và ngược lại).
3. Các trường tên-quan-trọng (province_name / district_name / ward_name +
   type_name + admin_version) khác nhau cho cùng PK -> top 20 mẫu.

Usage:
    python scripts/diagnostics/diff_mat_old_vs_current.py
    python scripts/diagnostics/diff_mat_old_vs_current.py --levels ward
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

import psycopg2
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


LEVEL_CONFIG = {
    "province": {
        "pk": "province_id",
        "name_col": "province_name",
    },
    "district": {
        "pk": "district_id",
        "name_col": "district_name",
    },
    "ward": {
        "pk": "ward_id",
        "name_col": "ward_name",
    },
}


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        application_name="diff_mat_old_vs_current",
    )


def _table_has_column(conn, schema: str, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s AND column_name=%s",
            (schema, table, column),
        )
        return cur.fetchone() is not None


def diff_level(conn, level: str) -> None:
    cfg = LEVEL_CONFIG[level]
    pk = cfg["pk"]
    name_col = cfg["name_col"]
    cur_table = f"mat.{level}"
    old_table = f"mat.{level}_old"

    print(f"\n=== {old_table}  vs  {cur_table} ===")

    has_admin_version_cur = _table_has_column(conn, "mat", level, "admin_version")
    has_admin_version_old = _table_has_column(conn, "mat", f"{level}_old", "admin_version")

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {old_table}")
        old_n = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {cur_table}")
        cur_n = cur.fetchone()[0]
        print(f"  rows OLD       : {old_n:,}")
        print(f"  rows CURRENT   : {cur_n:,}")

        if has_admin_version_cur:
            cur.execute(
                f"SELECT admin_version, COUNT(*) FROM {cur_table} "
                f"GROUP BY admin_version ORDER BY admin_version"
            )
            for av, n in cur.fetchall():
                print(f"    CURRENT admin_version={av}: {n:,}")
        if has_admin_version_old:
            cur.execute(
                f"SELECT admin_version, COUNT(*) FROM {old_table} "
                f"GROUP BY admin_version ORDER BY admin_version"
            )
            for av, n in cur.fetchall():
                print(f"    OLD     admin_version={av}: {n:,}")

        cur.execute(
            f"SELECT COUNT(*) FROM {old_table} o "
            f"LEFT JOIN {cur_table} c ON c.{pk} = o.{pk} WHERE c.{pk} IS NULL"
        )
        only_old = cur.fetchone()[0]
        cur.execute(
            f"SELECT COUNT(*) FROM {cur_table} c "
            f"LEFT JOIN {old_table} o ON o.{pk} = c.{pk} WHERE o.{pk} IS NULL"
        )
        only_cur = cur.fetchone()[0]
        print(f"  ids only in OLD     : {only_old:,}")
        print(f"  ids only in CURRENT : {only_cur:,}")

        compare_cols = [name_col, "type_name"]
        if has_admin_version_cur and has_admin_version_old:
            compare_cols.append("admin_version")

        differs_clauses = " OR ".join(
            f"o.{c} IS DISTINCT FROM c.{c}" for c in compare_cols
        )
        select_cols = ", ".join(
            f"o.{c} AS old_{c}, c.{c} AS cur_{c}" for c in compare_cols
        )
        cur.execute(
            f"SELECT COUNT(*) FROM {old_table} o "
            f"JOIN {cur_table} c ON c.{pk} = o.{pk} "
            f"WHERE {differs_clauses}"
        )
        diff_n = cur.fetchone()[0]
        print(f"  rows with differing {compare_cols}: {diff_n:,}")

        if diff_n:
            cur.execute(
                f"SELECT o.{pk}, {select_cols} "
                f"FROM {old_table} o JOIN {cur_table} c ON c.{pk} = o.{pk} "
                f"WHERE {differs_clauses} ORDER BY o.{pk} LIMIT 20"
            )
            rows = cur.fetchall()
            print("  sample diffs (up to 20):")
            for r in rows:
                print("    ", r)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=list(LEVEL_CONFIG.keys()),
        default=list(LEVEL_CONFIG.keys()),
    )
    args = parser.parse_args()

    load_dotenv()
    conn = _connect()
    try:
        for level in args.levels:
            diff_level(conn, level)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
