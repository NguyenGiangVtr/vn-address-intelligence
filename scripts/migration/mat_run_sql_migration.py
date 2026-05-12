"""
Execute a UTF-8 SQL migration file against DB from repo .env (psycopg2).

Usage:
  python scripts/migration/mat_run_sql_migration.py \\
    scripts/migration/20260512_mat_dedupe_one_alive_row_per_business_id.sql
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sql_file", type=Path, help="Path to .sql file")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")

    import os

    try:
        import psycopg2
    except ImportError as e:
        raise SystemExit("Install psycopg2-binary: pip install psycopg2-binary") from e

    sql_path = args.sql_file if args.sql_file.is_absolute() else repo_root / args.sql_file
    if not sql_path.is_file():
        raise SystemExit(f"File not found: {sql_path}")

    body = sql_path.read_text(encoding="utf-8")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT") or "5432",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        dbname=os.getenv("DB_NAME"),
    )
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(body)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"OK: executed {sql_path}")


if __name__ == "__main__":
    main()
