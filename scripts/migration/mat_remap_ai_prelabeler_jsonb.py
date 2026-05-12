"""
Remap integer admin ids inside ai.prelabeler_testcases JSON columns (input, expected, …).

Uses mat.migration_remap_* tables (populated by 20260512_mat_remap_duplicate_business_ids.sql).
Fails if the same old integer maps to more than one new id across all remap tables.

Usage:
  python scripts/migration/mat_remap_ai_prelabeler_jsonb.py
  python scripts/migration/mat_remap_ai_prelabeler_jsonb.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _load_pairs(conn) -> dict[int, int]:
    mapping: dict[int, int] = {}

    def add_pair(old: int, new: int) -> None:
        if old in mapping and mapping[old] != new:
            raise SystemExit(f"Ambiguous remap for id {old}: {mapping[old]} vs {new}")
        mapping[old] = new

    for sql in (
        "SELECT old_province_id, new_province_id FROM mat.migration_remap_province",
        "SELECT old_district_id, new_district_id FROM mat.migration_remap_district",
        "SELECT old_ward_id, new_ward_id FROM mat.migration_remap_ward",
    ):
        rows = conn.execute(text(sql)).fetchall()
        for r in rows:
            add_pair(int(r[0]), int(r[1]))
    return mapping


def _remap_json_obj(obj, id_map: dict[int, int]):
    if isinstance(obj, dict):
        return {k: _remap_json_obj(v, id_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_remap_json_obj(v, id_map) for v in obj]
    if isinstance(obj, int) and obj in id_map:
        return id_map[obj]
    return obj


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    url = (
        f"postgresql://{os.getenv('DB_USER')}:{quote_plus(os.getenv('DB_PASS') or '')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT') or '5432'}/{os.getenv('DB_NAME')}"
    )
    engine = create_engine(url, pool_pre_ping=True)

    json_cols = ("input", "expected", "test_result", "predict_meta", "suggested")

    with engine.connect() as conn:
        id_map = _load_pairs(conn)
        if not id_map:
            print("No rows in mat.migration_remap_* — nothing to do.")
            return

        rows = conn.execute(
            text(f"SELECT id, {', '.join(json_cols)} FROM ai.prelabeler_testcases")
        ).mappings().all()

    updates = 0
    for row in rows:
        new_vals = {}
        changed = False
        for col in json_cols:
            raw = row.get(col)
            if raw is None:
                continue
            if isinstance(raw, str):
                data = json.loads(raw)
            elif isinstance(raw, (dict, list)):
                data = raw
            else:
                continue
            new_data = _remap_json_obj(data, id_map)
            if new_data != data:
                changed = True
                new_vals[col] = json.dumps(new_data, ensure_ascii=False)
        if not changed:
            continue
        updates += 1
        if args.dry_run:
            print(f"would update id={row['id']}")
            continue
        sets = ", ".join(f"{c} = CAST(:{c} AS jsonb)" for c in new_vals)
        params = {**new_vals, "id": row["id"]}
        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE ai.prelabeler_testcases SET {sets}, updated_at = NOW() WHERE id = :id"),
                params,
            )

    label = "to update (dry-run)" if args.dry_run else "updated"
    print(f"Done. Rows {label}: {updates}; remap keys: {len(id_map)}")


if __name__ == "__main__":
    main()
