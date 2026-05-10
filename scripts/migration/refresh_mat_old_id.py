#!/usr/bin/env python3
"""
refresh_mat_old_id.py
=====================

Tái suy ra cột `mat.<level>.old_id` cho 3 bảng master hành chính trên DB mới
bằng cách so khớp tên với snapshot `mat.<level>_old` đã clone từ OLD DB
(`scripts/migration/clone_old_mat_tables.py`).

Cách làm (cascade từ cấp lớn -> cấp nhỏ):

    1. mat.province
       JOIN mat.province_old qua (LOWER(name), admin_version).

    2. mat.district
       JOIN mat.district_old qua (LOWER(name), admin_version)
       VÀ scope thêm `district_old.province_id = province.old_id`
       (province.old_id vừa set ở bước 1) để khử trùng tên huyện giữa các tỉnh.

    3. mat.ward
       JOIN mat.ward_old qua (LOWER(name), admin_version)
       VÀ scope thêm `ward_old.district_id = district.old_id`
       (district.old_id vừa set ở bước 2) để khử trùng tên xã/phường giữa các
       huyện.

Tại mỗi cấp, chỉ chấp nhận cặp **1:1 không nhập nhằng** (window
`COUNT(*) OVER (PARTITION BY ...)` cả phía cur và phía old đều = 1). Cặp
nhập nhằng được đếm và in ra sample, KHÔNG ghi đè -> an toàn.

Phụ thuộc dữ liệu: phải chạy `clone_old_mat_tables.py` trước để có
`mat.province_old / mat.district_old / mat.ward_old`.

Usage:
    python scripts/migration/refresh_mat_old_id.py --dry-run
    python scripts/migration/refresh_mat_old_id.py
    python scripts/migration/refresh_mat_old_id.py --reset
    python scripts/migration/refresh_mat_old_id.py --only-null
    python scripts/migration/refresh_mat_old_id.py --levels district ward
    python scripts/migration/refresh_mat_old_id.py --show-samples 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SCHEMA = "mat"
SUFFIX = "_old"

LEVEL_ORDER = ("province", "district", "ward")

DEFAULT_ALIASES_PATH = Path(__file__).resolve().parent / "mat_old_id_aliases.json"

# Mỗi level: pk + name + parent (level cha + cột FK trỏ về cha trên bảng con).
LEVEL_CONFIG = {
    "province": {
        "table": "province",
        "pk": "province_id",
        "name_col": "province_name",
        "parent": None,
    },
    "district": {
        "table": "district",
        "pk": "district_id",
        "name_col": "district_name",
        "parent": ("province", "province_id"),
    },
    "ward": {
        "table": "ward",
        "pk": "ward_id",
        "name_col": "ward_name",
        "parent": ("district", "district_id"),
    },
}


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        application_name="refresh_mat_old_id",
    )


def _ensure_old_snapshot(conn, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=%s AND table_name=%s",
            (SCHEMA, f"{table}{SUFFIX}"),
        )
        if cur.fetchone() is None:
            raise SystemExit(
                f"Missing snapshot {SCHEMA}.{table}{SUFFIX}. "
                f"Chạy `python scripts/migration/clone_old_mat_tables.py` trước."
            )


def _ensure_old_id_column(conn, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s AND column_name='old_id'",
            (SCHEMA, table),
        )
        if cur.fetchone() is None:
            raise SystemExit(
                f"Bảng {SCHEMA}.{table} không có cột `old_id` -- không thể refresh."
            )


def _old_active_filter(conn, table: str, alias: str = "old") -> str:
    """Build SQL WHERE-fragment lọc các dòng còn `active` trên bảng `{table}_old`.

    Quy ước:
      - Luôn áp `is_deleted = FALSE` nếu cột tồn tại.
      - Nếu cột `is_active` có -> bổ sung `is_active = TRUE` (strict, theo yêu cầu).
      - Nếu cả 2 cột đều không có -> trả về `TRUE` (no-op).
    """

    full_table = f"{table}{SUFFIX}"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s "
            "  AND column_name IN ('is_active','is_deleted')",
            (SCHEMA, full_table),
        )
        cols = {r[0] for r in cur.fetchall()}
    parts = []
    if "is_active" in cols:
        parts.append(f"{alias}.is_active = TRUE")
    if "is_deleted" in cols:
        parts.append(f"{alias}.is_deleted = FALSE")
    return " AND ".join(parts) if parts else "TRUE"


def _vn_translate_template() -> str:
    """SQL template `translate(LOWER({x}), <vn>, <ascii>)` — fallback bỏ dấu
    tiếng Việt KHÔNG cần extension `unaccent` (chỉ dùng built-in `translate`).
    Map đóng theo bộ ký tự Vietnamese accented -> ASCII tương ứng.
    """
    groups = [
        ("a", "àáảãạâầấẩẫậăằắẳẵặ"),
        ("e", "èéẻẽẹêềếểễệ"),
        ("i", "ìíỉĩị"),
        ("o", "òóỏõọôồốổỗộơờớởỡợ"),
        ("u", "ùúủũụưừứửữự"),
        ("y", "ỳýỷỹỵ"),
        ("d", "đ"),
    ]
    src = "".join(chs for _, chs in groups)
    dst = "".join(base * len(chs) for base, chs in groups)
    if len(src) != len(dst):
        raise RuntimeError("VN translate map src/dst length mismatch")
    return f"translate(LOWER({{x}}), '{src}', '{dst}')"


def _detect_vn_normalizer(conn) -> tuple[str, str]:
    """Trả về (label, sql_template_with_{x}_placeholder).

    Ưu tiên `unaccent()` (extension); fallback `translate()` pure-SQL khi
    không có quyền `CREATE EXTENSION` (vẫn đủ để xử lý chênh lệch dấu
    unicode `oà`/`òa` v.v vì cả hai đều bỏ về `oa`).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE p.proname='unaccent' AND p.pronargs=1 LIMIT 1"
        )
        if cur.fetchone():
            return ("unaccent", "LOWER(unaccent({x}))")
    return ("translate-fallback", _vn_translate_template())


def _name_match_expr(name_col: str, mode: str, vn_norm_template: str) -> str:
    """SQL expression matching `old.{name_col}` against `cur.{name_col}`.

    `mode='exact'`    : BTRIM + LOWER  (preserve diacritics, strict).
    `mode='unaccent'` : BTRIM + `vn_norm_template` -- bỏ dấu để xử lý chênh
                        lệch unicode (`Hoà` vs `Hòa`...). `vn_norm_template`
                        đến từ `_detect_vn_normalizer()`.
    """

    if mode == "exact":
        return (
            f"BTRIM(LOWER(old.{name_col})) = BTRIM(LOWER(cur.{name_col}))"
        )
    if mode == "unaccent":
        old_norm = vn_norm_template.format(x=f"old.{name_col}")
        cur_norm = vn_norm_template.format(x=f"cur.{name_col}")
        return f"BTRIM({old_norm}) = BTRIM({cur_norm})"
    raise ValueError(f"Unknown name match mode: {mode}")


def _build_candidate_cte(
    level: str,
    only_null: bool,
    active_filter: str,
    name_match_mode: str = "exact",
    vn_norm_template: str = "LOWER({x})",
) -> str:
    """Trả về WITH cand AS (...) , counted AS (...) , unambiguous AS (...) -- KHÔNG kèm
    statement cuối; gọi nơi dùng tự nối thêm SELECT/UPDATE.

    `active_filter` đã được build sẵn từ `_old_active_filter()` (alias='old').
    `name_match_mode` -> xem `_name_match_expr` cho ý nghĩa.
    `vn_norm_template`  -> SQL template bỏ dấu (cho mode='unaccent').
    """

    cfg = LEVEL_CONFIG[level]
    table = cfg["table"]
    pk = cfg["pk"]
    name_col = cfg["name_col"]
    parent_cfg = cfg["parent"]

    null_filter = " AND cur.old_id IS NULL" if only_null else ""
    name_match = _name_match_expr(name_col, name_match_mode, vn_norm_template)

    if parent_cfg is None:
        join_block = f"""
            FROM {SCHEMA}.{table} cur
            JOIN {SCHEMA}.{table}{SUFFIX} old
              ON old.admin_version = cur.admin_version
             AND {name_match}
             AND ({active_filter})
            WHERE TRUE{null_filter}
        """
    else:
        parent_level, parent_fk = parent_cfg
        parent_table = LEVEL_CONFIG[parent_level]["table"]
        parent_pk = LEVEL_CONFIG[parent_level]["pk"]
        join_block = f"""
            FROM {SCHEMA}.{table} cur
            JOIN {SCHEMA}.{parent_table} cur_par
              ON cur_par.{parent_pk} = cur.{parent_fk}
             AND cur_par.admin_version = cur.admin_version
             AND cur_par.old_id IS NOT NULL
            JOIN {SCHEMA}.{table}{SUFFIX} old
              ON old.admin_version = cur.admin_version
             AND {name_match}
             AND old.{parent_fk} = cur_par.old_id
             AND ({active_filter})
            WHERE TRUE{null_filter}
        """

    return f"""
        WITH cand AS (
            SELECT cur.{pk}        AS cur_id,
                   cur.admin_version,
                   cur.{name_col}   AS cur_name,
                   old.{pk}        AS old_id_value
            {join_block}
        ),
        counted AS (
            SELECT cur_id,
                   admin_version,
                   cur_name,
                   old_id_value,
                   -- PK của mat.<level> thực tế là composite (id, admin_version),
                   -- nên partition cả hai để không nhầm 2 phiên bản v1/v2 cùng id
                   -- thành "ambiguous".
                   COUNT(*) OVER (PARTITION BY cur_id, admin_version)
                       AS dup_per_cur,
                   COUNT(*) OVER (PARTITION BY old_id_value, admin_version)
                       AS dup_per_old
            FROM cand
        ),
        unambiguous AS (
            SELECT cur_id, admin_version, old_id_value
            FROM counted
            WHERE dup_per_cur = 1 AND dup_per_old = 1
        )
    """


def _do_one_pass(
    conn,
    level: str,
    *,
    pass_label: str,
    name_match_mode: str,
    only_null: bool,
    dry_run: bool,
    show_samples: int,
    active_filter: str,
    vn_norm_template: str,
) -> dict:
    """Một lần quét cascade match (strict hoặc unaccent). Trả về stat dict."""

    cfg = LEVEL_CONFIG[level]
    table = cfg["table"]
    pk = cfg["pk"]
    name_col = cfg["name_col"]

    cte = _build_candidate_cte(
        level,
        only_null=only_null,
        active_filter=active_filter,
        name_match_mode=name_match_mode,
        vn_norm_template=vn_norm_template,
    )

    diag_sql = cte + """
        SELECT
            (SELECT COUNT(*) FROM
                (SELECT DISTINCT cur_id, admin_version FROM cand) AS d)
                AS candidate_cur,
            (SELECT COUNT(*)               FROM unambiguous) AS unambiguous_count,
            (SELECT COUNT(*) FROM
                (SELECT DISTINCT cur_id, admin_version FROM counted
                    WHERE dup_per_cur > 1 OR dup_per_old > 1) AS d)
                AS ambiguous_count
    """
    with conn.cursor() as cur:
        cur.execute(diag_sql)
        candidate_cur, unambiguous_count, ambiguous_count = cur.fetchone()

    name_match_only = _name_match_expr(name_col, name_match_mode, vn_norm_template)
    unmatched_filter = " AND cur.old_id IS NULL" if only_null else ""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*) FROM {SCHEMA}.{table} cur
            WHERE NOT EXISTS (
                SELECT 1 FROM {SCHEMA}.{table}{SUFFIX} old
                WHERE old.admin_version = cur.admin_version
                  AND {name_match_only}
                  AND ({active_filter})
            ){unmatched_filter}
        """)
        unmatched_no_name = cur.fetchone()[0]

    print(f"  [{pass_label}] mode={name_match_mode} only_null={only_null}")
    print(f"    candidate cur rows (>=1 name match): {candidate_cur:,}")
    print(f"    unambiguous 1:1 matches            : {unambiguous_count:,}")
    print(f"    ambiguous (skipped)                : {ambiguous_count:,}")
    print(f"    unmatched (no name in old at all)  : {unmatched_no_name:,}")

    if show_samples > 0 and ambiguous_count:
        with conn.cursor() as cur:
            cur.execute(cte + f"""
                SELECT cur_id, admin_version, cur_name, old_id_value,
                       dup_per_cur, dup_per_old
                FROM counted
                WHERE dup_per_cur > 1 OR dup_per_old > 1
                ORDER BY admin_version, cur_id, old_id_value
                LIMIT {int(show_samples)}
            """)
            rows = cur.fetchall()
        print(f"    sample ambiguous (up to {show_samples}):")
        for r in rows:
            print(f"      cur_id={r[0]} av={r[1]} name={r[2]!r} "
                  f"old_id={r[3]} dup_cur={r[4]} dup_old={r[5]}")

    updated = 0
    if not dry_run and unambiguous_count:
        change_filter = (
            "AND t.old_id IS NULL" if only_null
            else "AND t.old_id IS DISTINCT FROM u.old_id_value"
        )
        update_sql = cte + f"""
            UPDATE {SCHEMA}.{table} t
            SET old_id = u.old_id_value
            FROM unambiguous u
            WHERE t.{pk} = u.cur_id
              AND t.admin_version = u.admin_version
              {change_filter}
        """
        with conn.cursor() as cur:
            cur.execute(update_sql)
            updated = cur.rowcount
        conn.commit()
        print(f"    UPDATE rows changed                : {updated:,}")
    elif dry_run:
        print("    DRY-RUN: skipping UPDATE")

    return {
        "candidate_cur": candidate_cur,
        "unambiguous": unambiguous_count,
        "ambiguous": ambiguous_count,
        "unmatched_no_name": unmatched_no_name,
        "updated": updated,
    }


def _load_aliases(path: Path) -> dict:
    """Load alias JSON. Trả về dict rỗng nếu file không tồn tại."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if isinstance(v, list)}


def _apply_aliases(
    conn,
    level: str,
    aliases: list,
    active_filter: str,
    dry_run: bool,
) -> int:
    """Apply manual name-based aliases (PRE-cascade). Chỉ ghi vào dòng `old_id IS NULL`.

    Mỗi entry: {admin_version, cur_name, old_name}.
    Sub-level optional: {parent_old_name} -> scope qua tên cha trên `_old`.

    Trả về số dòng đã update.
    """
    if not aliases:
        return 0

    cfg = LEVEL_CONFIG[level]
    table = cfg["table"]
    pk = cfg["pk"]
    name_col = cfg["name_col"]
    parent_cfg = cfg["parent"]

    print(f"  [aliases] {len(aliases)} entry(ies) cấu hình cho level={level}")
    total_updated = 0

    for i, entry in enumerate(aliases):
        if not all(k in entry for k in ("admin_version", "cur_name", "old_name")):
            print(f"    skip entry #{i}: thiếu key bắt buộc {entry!r}")
            continue

        params = {
            "av": entry["admin_version"],
            "cur_name": entry["cur_name"],
            "old_name": entry["old_name"],
        }

        if parent_cfg is None:
            update_sql = f"""
                UPDATE {SCHEMA}.{table} cur
                SET old_id = src.{pk}
                FROM (
                    SELECT {pk} FROM {SCHEMA}.{table}{SUFFIX}
                    WHERE admin_version = %(av)s
                      AND BTRIM(LOWER({name_col})) = BTRIM(LOWER(%(old_name)s))
                      AND ({active_filter.replace('old.', '')})
                    LIMIT 1
                ) src
                WHERE cur.admin_version = %(av)s
                  AND BTRIM(LOWER(cur.{name_col})) = BTRIM(LOWER(%(cur_name)s))
                  AND cur.old_id IS NULL
            """
        else:
            parent_old_name = entry.get("parent_old_name")
            if not parent_old_name:
                print(f"    skip entry #{i}: sub-level cần `parent_old_name`")
                continue
            parent_level, parent_fk = parent_cfg
            parent_table = LEVEL_CONFIG[parent_level]["table"]
            parent_name_col = LEVEL_CONFIG[parent_level]["name_col"]
            parent_pk = LEVEL_CONFIG[parent_level]["pk"]
            params["parent_old_name"] = parent_old_name
            update_sql = f"""
                UPDATE {SCHEMA}.{table} cur
                SET old_id = src.{pk}
                FROM (
                    SELECT o.{pk}
                    FROM {SCHEMA}.{table}{SUFFIX} o
                    JOIN {SCHEMA}.{parent_table}{SUFFIX} po
                      ON po.{parent_pk} = o.{parent_fk}
                     AND po.admin_version = o.admin_version
                    WHERE o.admin_version = %(av)s
                      AND BTRIM(LOWER(o.{name_col})) = BTRIM(LOWER(%(old_name)s))
                      AND BTRIM(LOWER(po.{parent_name_col}))
                          = BTRIM(LOWER(%(parent_old_name)s))
                      AND ({active_filter.replace('old.', 'o.')})
                    LIMIT 1
                ) src
                WHERE cur.admin_version = %(av)s
                  AND BTRIM(LOWER(cur.{name_col})) = BTRIM(LOWER(%(cur_name)s))
                  AND cur.old_id IS NULL
            """

        if dry_run:
            print(f"    DRY-RUN entry #{i}: {entry.get('cur_name')!r} -> "
                  f"{entry.get('old_name')!r} (av={entry['admin_version']})")
            continue

        with conn.cursor() as cur:
            cur.execute(update_sql, params)
            n = cur.rowcount
        conn.commit()
        total_updated += n
        msg = f"    entry #{i}: {entry.get('cur_name')!r} -> " \
              f"{entry.get('old_name')!r} (av={entry['admin_version']}) -> {n} row(s)"
        if entry.get("comment"):
            msg += f"  // {entry['comment']}"
        print(msg)

    print(f"  [aliases] total rows updated: {total_updated}")
    return total_updated


def refresh_level(
    conn,
    level: str,
    *,
    dry_run: bool = False,
    only_null: bool = False,
    reset: bool = False,
    show_samples: int = 0,
    lenient: bool = False,
    vn_norm_template: str = "LOWER({x})",
    aliases: Optional[list] = None,
) -> dict:
    """Set-based refresh `mat.<level>.old_id` từ `mat.<level>_old`.

    Cascade strict (pass 1, exact name).
    Tuỳ chọn `lenient=True` -> pass 2 unaccent() chỉ trên các dòng vẫn còn
    `old_id IS NULL` sau pass 1 (giúp xử lý chênh lệch vị trí dấu unicode
    kiểu `Hoà` vs `Hòa`).
    """

    cfg = LEVEL_CONFIG[level]
    table = cfg["table"]

    _ensure_old_snapshot(conn, table)
    _ensure_old_id_column(conn, table)

    if cfg["parent"] is not None:
        parent_table = LEVEL_CONFIG[cfg["parent"][0]]["table"]
        _ensure_old_id_column(conn, parent_table)

    print(f"\n=== {SCHEMA}.{table}  (parent={cfg['parent']}) ===")

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table} WHERE old_id IS NOT NULL")
        before_set = cur.fetchone()[0]
    print(f"  rows total                         : {total:,}")
    print(f"  old_id IS NOT NULL (before)        : {before_set:,}")

    if reset and not dry_run:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {SCHEMA}.{table} SET old_id = NULL WHERE old_id IS NOT NULL"
            )
            print(f"  reset                              : NULLed {cur.rowcount:,} rows")
        conn.commit()

    active_filter = _old_active_filter(conn, table, alias="old")
    print(f"  active filter on {table}{SUFFIX:<10}: {active_filter}")

    aliases_updated = _apply_aliases(
        conn, level, aliases or [], active_filter=active_filter, dry_run=dry_run,
    )

    pass1 = _do_one_pass(
        conn, level,
        pass_label="pass1/strict",
        name_match_mode="exact",
        only_null=only_null,
        dry_run=dry_run,
        show_samples=show_samples,
        active_filter=active_filter,
        vn_norm_template=vn_norm_template,
    )

    pass2 = None
    if lenient:
        pass2 = _do_one_pass(
            conn, level,
            pass_label="pass2/unaccent",
            name_match_mode="unaccent",
            only_null=True,
            dry_run=dry_run,
            show_samples=show_samples,
            active_filter=active_filter,
            vn_norm_template=vn_norm_template,
        )

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table} WHERE old_id IS NOT NULL")
        after_set = cur.fetchone()[0]
    print(f"  old_id IS NOT NULL (after)         : {after_set:,}")

    return {
        "level": level,
        "total": total,
        "before_set": before_set,
        "aliases_updated": aliases_updated,
        "pass1_unambiguous": pass1["unambiguous"],
        "pass1_ambiguous": pass1["ambiguous"],
        "pass1_no_name": pass1["unmatched_no_name"],
        "pass1_updated": pass1["updated"],
        "pass2_unambiguous": (pass2 or {}).get("unambiguous", 0),
        "pass2_updated": (pass2 or {}).get("updated", 0),
        "after_set": after_set,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--levels", nargs="+", choices=list(LEVEL_ORDER),
        default=list(LEVEL_ORDER),
        help="Subset of levels to refresh; cascade order là province->district->ward.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Chỉ in chẩn đoán, không UPDATE.")
    parser.add_argument("--only-null", action="store_true",
                        help="Chỉ ghi vào dòng đang có old_id IS NULL.")
    parser.add_argument("--reset", action="store_true",
                        help="NULL toàn bộ old_id của level trước khi refresh.")
    parser.add_argument("--show-samples", type=int, default=0, metavar="N",
                        help="Print N hàng nhập nhằng làm mẫu (default 0).")
    parser.add_argument("--lenient", action="store_true",
                        help="Sau pass strict, chạy pass 2 dùng unaccent() cho "
                             "các dòng vẫn NULL (xử lý chênh dấu unicode).")
    parser.add_argument(
        "--aliases-file", type=Path, default=DEFAULT_ALIASES_PATH,
        help=f"JSON file alias thủ công (default: {DEFAULT_ALIASES_PATH.name}). "
             "Set thành đường dẫn không tồn tại để bỏ qua aliases.",
    )
    args = parser.parse_args()

    if args.dry_run and args.reset:
        print("--dry-run + --reset: chỉ in chẩn đoán, KHÔNG NULL old_id.")

    levels = sorted(set(args.levels), key=LEVEL_ORDER.index)

    load_dotenv()
    print(f"Refresh mat.*.old_id  ({datetime.now().isoformat(timespec='seconds')})")
    print(f"  TARGET DB : {os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")
    print(f"  LEVELS    : {', '.join(levels)} (cascade order enforced)")
    if args.dry_run:
        print("  MODE      : DRY-RUN")
    if args.only_null:
        print("  MODE      : --only-null (giữ nguyên old_id đã có)")
    if args.reset:
        print("  MODE      : --reset (NULL toàn bộ old_id trước)")
    if args.lenient:
        print("  MODE      : --lenient (pass 2 unaccent fallback)")

    conn = _connect()
    conn.autocommit = False
    try:
        norm_label, vn_norm_template = _detect_vn_normalizer(conn)
        if args.lenient:
            print(f"  NORMALIZER: {norm_label}")

        all_aliases = _load_aliases(args.aliases_file)
        if all_aliases:
            print(f"  ALIASES   : {args.aliases_file}  "
                  f"({sum(len(v) for v in all_aliases.values())} entries total)")
        else:
            print(f"  ALIASES   : (none) — file {args.aliases_file} not found "
                  f"or empty")

        results = []
        for level in levels:
            results.append(refresh_level(
                conn, level,
                dry_run=args.dry_run,
                only_null=args.only_null,
                reset=args.reset,
                show_samples=args.show_samples,
                lenient=args.lenient,
                vn_norm_template=vn_norm_template,
                aliases=all_aliases.get(level, []),
            ))
        print("\n=== SUMMARY ===")
        print(f"  {'level':<10} {'total':>7} {'aliases':>7} "
              f"{'p1_unamb':>9} {'p1_amb':>7} {'p1_upd':>7} "
              f"{'p2_unamb':>9} {'p2_upd':>7} {'after_set':>10}")
        for r in results:
            print(
                f"  {r['level']:<10} {r['total']:>7,} "
                f"{r['aliases_updated']:>7,} "
                f"{r['pass1_unambiguous']:>9,} {r['pass1_ambiguous']:>7,} "
                f"{r['pass1_updated']:>7,} "
                f"{r['pass2_unambiguous']:>9,} {r['pass2_updated']:>7,} "
                f"{r['after_set']:>10,}"
            )
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
