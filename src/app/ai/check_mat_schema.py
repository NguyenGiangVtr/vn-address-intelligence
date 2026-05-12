"""One-off admin schema inspection; run via repo root with `python -m app.ai.check_mat_schema`."""

import sys
from pathlib import Path

for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
import _bootstrap_import_paths  # noqa: E402

_bootstrap_import_paths.install()

import psycopg2

from app.ai.utils.config_loader import load_config_with_env
from app.paths import ai_config_yaml

cfg = load_config_with_env(str(ai_config_yaml()))["database"]

conn = psycopg2.connect(
    host=cfg["host"], port=cfg["port"],
    dbname=cfg["dbname"], user=cfg["user"], password=cfg["password"]
)
cur = conn.cursor()

for table in ["mat.province", "mat.district", "mat.ward"]:
    print(f"\n=== Columns of {table} ===")
    parts = table.split(".")
    schema, tname = parts[0], parts[1]
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{tname}'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:<20} {r[1]}")

cur.close()
conn.close()
