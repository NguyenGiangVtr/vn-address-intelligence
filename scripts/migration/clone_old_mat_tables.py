#!/usr/bin/env python3
"""
clone_old_mat_tables.py
=======================

Clone snapshot 3 bảng master hành chính từ OLD database (gse_sprint trên
10.10.13.126) sang NEW database (vn_address_intelligence_db trên 157.66.81.69)
với suffix `_old` trong cùng schema `mat` để dễ đối chiếu / hồi phục dữ liệu
khi master mới bị cập nhật sai.

Mặc định clone:
    OLD: mat.province  -> NEW: mat.province_old
    OLD: mat.district  -> NEW: mat.district_old
    OLD: mat.ward      -> NEW: mat.ward_old

Quy ước:
- Đọc cấu hình kết nối từ biến môi trường `.env`:
    OLD_DB_HOST / OLD_DB_PORT / OLD_DB_USER / OLD_DB_PASS / OLD_DB_NAME
    DB_HOST     / DB_PORT     / DB_USER     / DB_PASS     / DB_NAME
- DDL được tái tạo nguyên gốc bằng `format_type(atttypid, atttypmod)` để giữ
  đúng kiểu (jsonb / timestamp / numeric / character varying(N) ...).
- Dữ liệu chuyển bằng `COPY ... TO STDOUT WITH (FORMAT BINARY)` rồi
  `COPY ... FROM STDIN WITH (FORMAT BINARY)` qua bộ nhớ — tránh phiền phức
  encoding/CSV escaping cho cột JSONB.
- Idempotent: `DROP TABLE IF EXISTS mat.<table>_old CASCADE` trước khi tạo lại.
- Sau khi load, tạo thêm INDEX trên `(admin_version, old_id)` và `(<pk_col>)`
  để truy vấn cross-check nhanh; bảng `_old` chỉ là **read-only snapshot**,
  không tạo PRIMARY KEY / FK / sequence.
- Verify: row count NEW phải khớp row count OLD; nếu lệch -> exit code 2.

Usage:
    python scripts/migration/clone_old_mat_tables.py
    python scripts/migration/clone_old_mat_tables.py --tables ward
    python scripts/migration/clone_old_mat_tables.py --dry-run
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime
from typing import List, Sequence

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql


DEFAULT_TABLES: tuple[str, ...] = ("province", "district", "ward")
SOURCE_SCHEMA = "mat"
TARGET_SCHEMA = "mat"
TARGET_SUFFIX = "_old"


def _connect(prefix: str) -> psycopg2.extensions.connection:
    """Mở connection từ biến môi trường <PREFIX>_DB_*.

    `prefix=""`  -> đọc DB_HOST / DB_PORT / ...
    `prefix="OLD"` -> đọc OLD_DB_HOST / OLD_DB_PORT / ...
    """

    pfx = f"{prefix}_" if prefix else ""
    host = os.getenv(f"{pfx}DB_HOST")
    port = os.getenv(f"{pfx}DB_PORT", "5432")
    user = os.getenv(f"{pfx}DB_USER")
    password = os.getenv(f"{pfx}DB_PASS")
    dbname = os.getenv(f"{pfx}DB_NAME")

    missing = [k for k, v in {
        f"{pfx}DB_HOST": host,
        f"{pfx}DB_USER": user,
        f"{pfx}DB_PASS": password,
        f"{pfx}DB_NAME": dbname,
    }.items() if not v]
    if missing:
        raise SystemExit(
            f"Missing env var(s) for {prefix or 'NEW'} database: {', '.join(missing)}"
        )

    conn = psycopg2.connect(
        host=host,
        port=int(port),
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=15,
        application_name="clone_old_mat_tables",
    )
    conn.autocommit = False
    return conn


def _fetch_columns(conn, schema: str, table: str) -> List[dict]:
    """Trả về list cột (name, type_decl, not_null) theo đúng thứ tự attnum."""

    sql_text = """
        SELECT a.attname            AS column_name,
               format_type(a.atttypid, a.atttypmod) AS type_decl,
               a.attnotnull         AS not_null
        FROM pg_attribute a
        JOIN pg_class     c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
          AND c.relname = %s
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY a.attnum
    """
    with conn.cursor() as cur:
        cur.execute(sql_text, (schema, table))
        rows = cur.fetchall()
    if not rows:
        raise RuntimeError(
            f"Table {schema}.{table} not found on source DB (or no columns)."
        )
    return [
        {"column_name": r[0], "type_decl": r[1], "not_null": bool(r[2])}
        for r in rows
    ]


def _fetch_pk_columns(conn, schema: str, table: str) -> List[str]:
    """Lấy các cột PK (theo thứ tự) — dùng để tạo index helper trên bảng _old."""

    sql_text = """
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_class     c ON c.oid = i.indrelid
        JOIN   pg_namespace n ON n.oid = c.relnamespace
        JOIN   pg_attribute a
               ON a.attrelid = i.indrelid
              AND a.attnum   = ANY(i.indkey)
        WHERE  i.indisprimary
          AND  n.nspname = %s
          AND  c.relname = %s
        ORDER  BY array_position(i.indkey, a.attnum)
    """
    with conn.cursor() as cur:
        cur.execute(sql_text, (schema, table))
        return [r[0] for r in cur.fetchall()]


def _row_count(conn, schema: str, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                sql.Identifier(schema), sql.Identifier(table)
            )
        )
        return int(cur.fetchone()[0])


def _build_create_ddl(columns: Sequence[dict], target_schema: str, target_table: str) -> sql.Composed:
    """Build `CREATE TABLE` chỉ với column-level NOT NULL — không kéo theo PK/FK."""

    col_defs: List[sql.Composed] = []
    for col in columns:
        parts: List[sql.Composable] = [
            sql.Identifier(col["column_name"]),
            sql.SQL(col["type_decl"]),
        ]
        if col["not_null"]:
            parts.append(sql.SQL("NOT NULL"))
        col_defs.append(sql.SQL(" ").join(parts))

    return sql.SQL("CREATE TABLE {}.{} (\n  {}\n)").format(
        sql.Identifier(target_schema),
        sql.Identifier(target_table),
        sql.SQL(",\n  ").join(col_defs),
    )


def _stream_copy_binary(
    src_conn,
    src_schema: str,
    src_table: str,
    dst_conn,
    dst_schema: str,
    dst_table: str,
) -> None:
    """Copy toàn bộ rows OLD -> NEW qua buffer BINARY trong RAM.

    3 bảng master tối đa ~10K rows mỗi cái -> dung lượng nhỏ, an toàn cho RAM.
    """

    buf = io.BytesIO()
    src_copy = sql.SQL("COPY {}.{} TO STDOUT WITH (FORMAT BINARY)").format(
        sql.Identifier(src_schema), sql.Identifier(src_table)
    )
    dst_copy = sql.SQL("COPY {}.{} FROM STDIN WITH (FORMAT BINARY)").format(
        sql.Identifier(dst_schema), sql.Identifier(dst_table)
    )

    with src_conn.cursor() as src_cur:
        src_cur.copy_expert(src_copy, buf)
    buf.seek(0)
    with dst_conn.cursor() as dst_cur:
        dst_cur.copy_expert(dst_copy, buf)


def _create_lookup_indexes(
    conn,
    target_schema: str,
    target_table: str,
    columns: Sequence[dict],
    pk_cols: Sequence[str],
) -> None:
    """Tạo index helper trên (admin_version, old_id) và PK gốc nếu có."""

    col_names = {c["column_name"] for c in columns}
    statements: List[sql.Composed] = []

    if {"admin_version", "old_id"}.issubset(col_names):
        statements.append(
            sql.SQL("CREATE INDEX {} ON {}.{} (admin_version, old_id)").format(
                sql.Identifier(f"ix_{target_table}_av_oldid"),
                sql.Identifier(target_schema),
                sql.Identifier(target_table),
            )
        )

    if pk_cols and all(c in col_names for c in pk_cols):
        statements.append(
            sql.SQL("CREATE INDEX {} ON {}.{} ({})").format(
                sql.Identifier(f"ix_{target_table}_pk_lookup"),
                sql.Identifier(target_schema),
                sql.Identifier(target_table),
                sql.SQL(", ").join(sql.Identifier(c) for c in pk_cols),
            )
        )

    if not statements:
        return
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)


def _add_table_comment(
    conn,
    target_schema: str,
    target_table: str,
    src_host: str,
    src_db: str,
    src_table: str,
    rows: int,
) -> None:
    note = (
        f"Snapshot of {src_db}.{SOURCE_SCHEMA}.{src_table} from host {src_host}, "
        f"cloned at {datetime.now().isoformat(timespec='seconds')} ({rows:,} rows). "
        f"Source: scripts/migration/clone_old_mat_tables.py"
    )
    stmt = sql.SQL("COMMENT ON TABLE {}.{} IS {}").format(
        sql.Identifier(target_schema),
        sql.Identifier(target_table),
        sql.Literal(note),
    )
    with conn.cursor() as cur:
        cur.execute(stmt)


def clone_table(
    src_conn,
    dst_conn,
    table: str,
    *,
    dry_run: bool,
    src_host: str,
    src_db: str,
) -> dict:
    target_table = f"{table}{TARGET_SUFFIX}"

    print(f"\n=== {SOURCE_SCHEMA}.{table}  ->  {TARGET_SCHEMA}.{target_table} ===")
    columns = _fetch_columns(src_conn, SOURCE_SCHEMA, table)
    pk_cols = _fetch_pk_columns(src_conn, SOURCE_SCHEMA, table)
    src_rows = _row_count(src_conn, SOURCE_SCHEMA, table)
    print(f"  source rows : {src_rows:,}")
    print(f"  source cols : {len(columns)}  (PK: {pk_cols or '<none>'})")

    create_ddl = _build_create_ddl(columns, TARGET_SCHEMA, target_table)

    if dry_run:
        print("  DRY-RUN -- would execute:")
        print("    DROP TABLE IF EXISTS "
              f"{TARGET_SCHEMA}.{target_table} CASCADE")
        print("    " + create_ddl.as_string(dst_conn).replace("\n", "\n    "))
        print(f"    COPY {SOURCE_SCHEMA}.{table} -> "
              f"{TARGET_SCHEMA}.{target_table} (BINARY)")
        return {
            "table": table,
            "src_rows": src_rows,
            "dst_rows": None,
            "status": "dry-run",
        }

    with dst_conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
            sql.Identifier(TARGET_SCHEMA)
        ))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
            sql.Identifier(TARGET_SCHEMA), sql.Identifier(target_table)
        ))
        cur.execute(create_ddl)
    print(f"  recreated {TARGET_SCHEMA}.{target_table}")

    print("  copying data (BINARY) ...", end=" ", flush=True)
    _stream_copy_binary(
        src_conn, SOURCE_SCHEMA, table,
        dst_conn, TARGET_SCHEMA, target_table,
    )
    print("done.")

    _create_lookup_indexes(dst_conn, TARGET_SCHEMA, target_table, columns, pk_cols)
    _add_table_comment(
        dst_conn, TARGET_SCHEMA, target_table,
        src_host=src_host, src_db=src_db, src_table=table, rows=src_rows,
    )
    dst_conn.commit()

    dst_rows = _row_count(dst_conn, TARGET_SCHEMA, target_table)
    status = "ok" if dst_rows == src_rows else "MISMATCH"
    print(f"  verified rows: src={src_rows:,}  dst={dst_rows:,}  -> {status}")
    return {
        "table": table,
        "src_rows": src_rows,
        "dst_rows": dst_rows,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Clone mat.province / mat.district / mat.ward from OLD_DB into "
            "the new DB as mat.*_old read-only snapshots."
        )
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=DEFAULT_TABLES,
        default=list(DEFAULT_TABLES),
        help="Subset of mat.* tables to clone (default: all three).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be executed without touching the new DB.",
    )
    args = parser.parse_args()

    load_dotenv()

    src_host = os.getenv("OLD_DB_HOST")
    src_db = os.getenv("OLD_DB_NAME")
    dst_host = os.getenv("DB_HOST")
    dst_db = os.getenv("DB_NAME")

    print(f"Clone mat.* OLD -> NEW  ({datetime.now().isoformat(timespec='seconds')})")
    print(f"  SOURCE : {src_host}/{src_db}  schema={SOURCE_SCHEMA}")
    print(f"  TARGET : {dst_host}/{dst_db}  schema={TARGET_SCHEMA}  suffix={TARGET_SUFFIX}")
    print(f"  TABLES : {', '.join(args.tables)}")
    if args.dry_run:
        print("  MODE   : DRY-RUN (no writes)")

    src_conn = _connect("OLD")
    dst_conn = _connect("")

    try:
        # Read-only safety on the OLD side.
        with src_conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")

        results: List[dict] = []
        for table in args.tables:
            try:
                results.append(clone_table(
                    src_conn, dst_conn, table,
                    dry_run=args.dry_run,
                    src_host=src_host, src_db=src_db,
                ))
            except Exception:
                dst_conn.rollback()
                raise

        print("\n=== SUMMARY ===")
        print(f"  {'table':<10} {'src_rows':>10} {'dst_rows':>10}  status")
        any_mismatch = False
        for r in results:
            dst = "-" if r["dst_rows"] is None else f"{r['dst_rows']:,}"
            print(
                f"  {r['table']:<10} {r['src_rows']:>10,} {dst:>10}  {r['status']}"
            )
            if r["status"] not in {"ok", "dry-run"}:
                any_mismatch = True
        return 2 if any_mismatch else 0
    finally:
        try:
            src_conn.close()
        except Exception:
            pass
        try:
            dst_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
