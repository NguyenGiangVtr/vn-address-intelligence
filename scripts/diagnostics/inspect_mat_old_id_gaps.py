#!/usr/bin/env python3
"""
inspect_mat_old_id_gaps.py
==========================

In ra các dòng `mat.<level>` còn `old_id IS NULL` sau khi chạy
`refresh_mat_old_id.py`, kèm theo gợi ý ứng viên gần nhất từ
`mat.<level>_old` (cùng admin_version, gần tên — bằng pg_trgm similarity
nếu extension có, nếu không fallback so sánh tên thường).

Usage:
    python scripts/diagnostics/inspect_mat_old_id_gaps.py
    python scripts/diagnostics/inspect_mat_old_id_gaps.py --levels province
    python scripts/diagnostics/inspect_mat_old_id_gaps.py --limit 30
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SCHEMA = "mat"
SUFFIX = "_old"

LEVEL_CONFIG = {
    "province": {"pk": "province_id", "name_col": "province_name", "parent_fk": None},
    "district": {"pk": "district_id", "name_col": "district_name", "parent_fk": "province_id"},
    "ward":     {"pk": "ward_id",     "name_col": "ward_name",     "parent_fk": "district_id"},
}


def _connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        application_name="inspect_mat_old_id_gaps",
    )


def _has_pg_trgm(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'")
        return cur.fetchone() is not None


def inspect(conn, level: str, limit: int) -> None:
    cfg = LEVEL_CONFIG[level]
    pk = cfg["pk"]
    name_col = cfg["name_col"]
    parent_fk = cfg["parent_fk"]

    print(f"\n=== {SCHEMA}.{level}  (NULL old_id) ===")

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) FROM {SCHEMA}.{level} WHERE old_id IS NULL"
        )
        n = cur.fetchone()[0]
    print(f"  total NULL old_id: {n:,}")

    use_trgm = _has_pg_trgm(conn)
    score_expr = (
        f"similarity(LOWER(o.{name_col}), LOWER(g.cur_name))" if use_trgm
        else f"CASE WHEN LOWER(o.{name_col})=LOWER(g.cur_name) THEN 1.0 ELSE 0.0 END"
    )

    parent_select = f", c.{parent_fk} AS parent_id" if parent_fk else ""

    sql = f"""
        WITH gaps AS (
            SELECT c.{pk}     AS cur_id,
                   c.admin_version,
                   c.{name_col} AS cur_name
                   {parent_select}
            FROM {SCHEMA}.{level} c
            WHERE c.old_id IS NULL
            ORDER BY c.admin_version, c.{pk}
            LIMIT %s
        ),
        scored AS (
            SELECT g.cur_id, g.admin_version, g.cur_name,
                   o.{pk} AS old_pk, o.{name_col} AS old_name,
                   {score_expr} AS score,
                   ROW_NUMBER() OVER (
                     PARTITION BY g.cur_id, g.admin_version
                     ORDER BY {score_expr} DESC NULLS LAST, o.{pk}
                   ) AS rn
            FROM gaps g
            LEFT JOIN {SCHEMA}.{level}{SUFFIX} o
              ON o.admin_version = g.admin_version
        )
        SELECT cur_id, admin_version, cur_name, old_pk, old_name, score
        FROM scored
        WHERE rn = 1
        ORDER BY admin_version, cur_id
    """

    with conn.cursor() as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()

    print(f"  using {'pg_trgm similarity' if use_trgm else 'exact match score'}; showing up to {limit}:")
    print(f"  {'cur_id':>7} {'av':>3} {'cur_name':<30} {'old_pk':>7} {'old_name':<30} score")
    for r in rows:
        cid, av, cname, opk, oname, sc = r
        score_str = f"{float(sc):.2f}" if sc is not None else "-"
        print(f"  {cid:>7} {av:>3} {str(cname)[:30]:<30} {str(opk):>7} "
              f"{str(oname or '-')[:30]:<30} {score_str}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--levels", nargs="+", choices=list(LEVEL_CONFIG.keys()),
        default=list(LEVEL_CONFIG.keys()),
    )
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    load_dotenv()

    conn = _connect()
    try:
        for level in args.levels:
            inspect(conn, level, args.limit)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
