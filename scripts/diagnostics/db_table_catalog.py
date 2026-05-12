"""
Dump PostgreSQL tables/views (non-system) with optional COMMENT ON TABLE/COLUMN.

Usage (from repo root, with .env loaded like app.core.config):
  python scripts/diagnostics/db_table_catalog.py
  python scripts/diagnostics/db_table_catalog.py --json
  python scripts/diagnostics/db_table_catalog.py --markdown docs/database-catalog.md
  python scripts/diagnostics/db_table_catalog.py --markdown --markdown-include-host
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path)


def _connect_url() -> str:
    import os

    user = os.getenv("DB_USER")
    pwd = quote_plus(os.getenv("DB_PASS") or "")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT") or "5432"
    name = os.getenv("DB_NAME")
    if not all([user, host, name]) or not os.getenv("DB_PASS"):
        raise SystemExit("Missing DB_USER/DB_PASS/DB_HOST/DB_NAME in environment or .env")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def _fetch_catalog(engine) -> tuple[list[dict], str | None]:
    """Return (payload, db_version_string_or_none)."""
    objects_sql = text(
        """
        SELECT n.nspname AS schema_name,
               c.relname AS rel_name,
               c.relkind AS rel_kind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p', 'v', 'm')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'temp', 'pg_toast')
        ORDER BY 1, 2;
        """
    )

    table_comment_sql = text(
        """
        SELECT n.nspname AS schema_name,
               c.relname AS rel_name,
               d.description AS table_comment
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
        WHERE c.relkind IN ('r', 'p', 'v', 'm')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'temp', 'pg_toast')
        ORDER BY 1, 2;
        """
    )

    column_sql = text(
        """
        SELECT n.nspname AS schema_name,
               c.relname AS rel_name,
               a.attname AS column_name,
               format_type(a.atttypid, a.atttypmod) AS data_type,
               col_description(c.oid, a.attnum) AS column_comment
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE a.attnum > 0
          AND NOT a.attisdropped
          AND c.relkind IN ('r', 'p', 'v', 'm')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'temp', 'pg_toast')
        ORDER BY 1, 2, a.attnum;
        """
    )

    with engine.connect() as conn:
        ver_row = conn.execute(text("SELECT version()")).fetchone()
        db_version = ver_row[0] if ver_row else None
        objs = conn.execute(objects_sql).mappings().all()
        tc_rows = conn.execute(table_comment_sql).mappings().all()
        col_rows = conn.execute(column_sql).mappings().all()

    table_comments: dict[tuple[str, str], str | None] = {}
    for r in tc_rows:
        table_comments[(r["schema_name"], r["rel_name"])] = r["table_comment"]

    cols_by_table: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in col_rows:
        cols_by_table[(r["schema_name"], r["rel_name"])].append(
            {
                "column_name": r["column_name"],
                "data_type": r["data_type"],
                "column_comment": r["column_comment"],
            }
        )

    payload: list[dict] = []
    for o in objs:
        key = (o["schema_name"], o["rel_name"])
        payload.append(
            {
                "schema": o["schema_name"],
                "name": o["rel_name"],
                "relkind": o["rel_kind"],
                "table_comment": table_comments.get(key),
                "columns": cols_by_table.get(key, []),
            }
        )
    return payload, db_version


def _kind_label(relkind: str) -> str:
    kind_map = {"r": "table", "p": "partitioned_table", "v": "view", "m": "materialized_view"}
    return kind_map.get(relkind, relkind)


def _format_item_md(item: dict) -> list[str]:
    fq = f"{item['schema']}.{item['name']}"
    rk = _kind_label(item["relkind"])
    lines: list[str] = [f"### `{fq}`", "", f"- **Loại:** {rk}", ""]
    tc = (item["table_comment"] or "").strip()
    if tc:
        lines.extend(["**COMMENT ON TABLE**", "", tc, ""])
    else:
        lines.extend(["*(Không có `COMMENT ON TABLE` trong DB.)*", ""])

    cols = item["columns"]
    commented = [c for c in cols if (c.get("column_comment") or "").strip()]
    show = commented[:20] if commented else cols[:12]
    lines.append("**Cột (mẫu / có comment)**")
    lines.append("")
    for c in show:
        cc = (c.get("column_comment") or "").strip()
        base = f"- `{c['column_name']}` (`{c['data_type']}`)"
        lines.append(base + (f" — {cc}" if cc else ""))
    if len(cols) > len(show):
        lines.append("")
        lines.append(f"*(… còn {len(cols) - len(show)} cột khác.)*")
    lines.append("")
    return lines


def _build_markdown(payload: list[dict], db_version: str | None, *, include_host: bool) -> str:
    import os

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    db_name = os.getenv("DB_NAME", "")
    db_host = os.getenv("DB_HOST", "")

    by_schema: dict[str, list[dict]] = defaultdict(list)
    for item in payload:
        by_schema[item["schema"]].append(item)

    table_rows: list[tuple[str, str]] = [
        ("Thời điểm xuất", now),
    ]
    if include_host and db_host:
        table_rows.append(("`DB_HOST`", f"`{db_host}`"))
    table_rows.append(("`DB_NAME`", f"`{db_name}`"))
    table_rows.append(("Số đối tượng", str(len(payload))))

    out: list[str] = [
        "# Danh mục bảng / view (PostgreSQL)",
        "",
        "File được sinh tự động bởi [`scripts/diagnostics/db_table_catalog.py`](../scripts/diagnostics/db_table_catalog.py).",
        "",
        "| Thuộc tính | Giá trị |",
        "|---|---|",
    ]
    for label, val in table_rows:
        out.append(f"| {label} | {val} |")
    out.append("")
    if db_version:
        out.extend(["**Phiên bản PostgreSQL**", "", db_version, ""])

    out.extend(
        [
            "## Tóm tắt theo schema",
            "",
        ]
    )
    for schema in sorted(by_schema.keys()):
        names = [f"`{i['schema']}.{i['name']}`" for i in sorted(by_schema[schema], key=lambda x: x["name"])]
        out.append(f"- **`{schema}`** ({len(names)}): {', '.join(names)}")
    out.append("")

    for schema in sorted(by_schema.keys()):
        out.append(f"## Schema `{schema}`")
        out.append("")
        for item in sorted(by_schema[schema], key=lambda x: x["name"]):
            out.extend(_format_item_md(item))

    return "\n".join(out).rstrip() + "\n"


def _print_text(payload: list[dict]) -> None:
    kind_map = {"r": "table", "p": "partitioned_table", "v": "view", "m": "materialized_view"}
    print(f"OBJECT_COUNT={len(payload)}")
    for item in payload:
        fq = f"{item['schema']}.{item['name']}"
        rk = kind_map.get(item["relkind"], item["relkind"])
        print(f"\n## {fq} ({rk})")
        tc = (item["table_comment"] or "").strip()
        if tc:
            print(tc)
        else:
            print("(no COMMENT ON TABLE)")
        cols = item["columns"]
        commented = [c for c in cols if (c.get("column_comment") or "").strip()]
        show = commented[:12] if commented else cols[:8]
        for c in show:
            cc = (c.get("column_comment") or "").strip()
            line = f" - {c['column_name']} ({c['data_type']})"
            if cc:
                line += f": {cc}"
            print(line)
        if len(cols) > len(show):
            print(f" ... ({len(cols) - len(show)} more columns)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument(
        "--markdown",
        metavar="PATH",
        nargs="?",
        const=str(Path(__file__).resolve().parents[2] / "docs" / "database-catalog.md"),
        help="Write Markdown catalog to PATH (default: docs/database-catalog.md)",
    )
    parser.add_argument(
        "--markdown-include-host",
        action="store_true",
        help="With --markdown, include DB_HOST in the header (default: omit for safety)",
    )
    args = parser.parse_args()

    _load_env()
    if not args.markdown:
        sys.stdout.reconfigure(encoding="utf-8")

    engine = create_engine(_connect_url(), pool_pre_ping=True)
    payload, db_version = _fetch_catalog(engine)

    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.markdown:
        md_path = Path(args.markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        body = _build_markdown(payload, db_version, include_host=args.markdown_include_host)
        md_path.write_text(body, encoding="utf-8")
        print(f"Wrote {md_path.resolve()} ({len(payload)} objects)")
        return

    _print_text(payload)


if __name__ == "__main__":
    main()
