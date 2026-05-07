"""Apply a .sql file to the configured PostgreSQL via SQLAlchemy.

Usage:
    python scripts/sql/apply_sql_file.py scripts/sql/alter_corpus_source_type_hf.sql
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

from app.core.database import engine


def split_statements(sql: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for raw_line in sql.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            buf = []
            if not stmt:
                continue
            if stmt.upper() in ("BEGIN", "COMMIT"):
                continue
            out.append(stmt)
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";").strip()
        if stmt and stmt.upper() not in ("BEGIN", "COMMIT"):
            out.append(stmt)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: apply_sql_file.py <path-to-sql>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    sql = path.read_text(encoding="utf-8")
    statements = split_statements(sql)
    print(f"-- Applying {path} ({len(statements)} statements)")

    with engine.begin() as conn:
        for i, stmt in enumerate(statements, 1):
            head = stmt.splitlines()[0][:100]
            print(f"[{i}/{len(statements)}] {head}")
            conn.execute(text(stmt))

    print("-- DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
