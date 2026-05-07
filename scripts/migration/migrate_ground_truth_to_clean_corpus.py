"""
Migrate prq.ground_truth -> prq.address_clean_corpus (idempotent upsert).

Rules:
- source_type is fixed to QUEUE_STANDARDIZED
- dedup key: (standardized_address, admin_epoch, source_type)
- address_components stores 10 required labels:
  NUM, STR, WDS, DST, PRO, NHB, BLD, POI, FLR, RM
"""

from __future__ import annotations

import argparse
import logging
import re
from typing import Any

from sqlalchemy import text

from app.core.database import SessionLocal

LOGGER = logging.getLogger("migrate_ground_truth_to_clean_corpus")

REQUIRED_LABELS = ("NUM", "STR", "WDS", "DST", "PRO", "NHB", "BLD", "POI", "FLR", "RM")


def _extract_components(address: str | None, province: str | None, district: str | None, ward: str | None) -> dict[str, Any]:
    addr = (address or "").strip()
    prov = (province or "").strip()
    dist = (district or "").strip()
    wrd = (ward or "").strip()
    out = {k: None for k in REQUIRED_LABELS}
    if not addr:
        return out

    # Extract simple house number prefix (e.g. "123", "12/5", "45A")
    num_match = re.match(r"^\s*([0-9]+(?:/[0-9A-Za-z]+)*)", addr)
    if num_match:
        out["NUM"] = num_match.group(1)

    # STR is remainder before first comma after removing NUM prefix
    head = addr.split(",")[0].strip()
    if out["NUM"] and head.startswith(out["NUM"]):
        head = head[len(out["NUM"]) :].strip(" -/")
    out["STR"] = head or None

    out["WDS"] = wrd or None
    out["DST"] = dist or None
    out["PRO"] = prov or None
    return out


def run(limit: int | None = None, admin_epoch: str = "2025", quality_score: float = 1.0) -> None:
    session = SessionLocal()
    inserted = 0
    updated = 0
    skipped = 0

    query = """
        SELECT
            g.id,
            g.address,
            g.province_id,
            g.district_id,
            g.ward_id,
            p.province_name,
            d.district_name,
            w.ward_name
        FROM prq.ground_truth g
        LEFT JOIN mat.province p ON p.old_id = g.province_id AND p.admin_version = 2
        LEFT JOIN mat.district d ON d.old_id = g.district_id AND d.admin_version = 2
        LEFT JOIN mat.ward w ON w.old_id = g.ward_id AND w.admin_version = 2
        WHERE g.address IS NOT NULL AND length(trim(g.address)) > 5
        ORDER BY g.id
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    try:
        rows = session.execute(text(query)).mappings().all()
        LOGGER.info("Loaded %d ground_truth rows", len(rows))

        upsert_sql = text(
            """
            INSERT INTO prq.address_clean_corpus (
                standardized_address,
                address_components,
                source_type,
                source_id,
                quality_score,
                province_id,
                province_name,
                district_id,
                district_name,
                ward_id,
                ward_name,
                admin_epoch,
                admin_version,
                created_by
            ) VALUES (
                :standardized_address,
                CAST(:address_components AS jsonb),
                'QUEUE_STANDARDIZED',
                :source_id,
                :quality_score,
                :province_id,
                :province_name,
                :district_id,
                :district_name,
                :ward_id,
                :ward_name,
                :admin_epoch,
                2,
                'GT_MIGRATION'
            )
            ON CONFLICT (standardized_address, admin_epoch, source_type)
            DO UPDATE SET
                source_id = EXCLUDED.source_id,
                address_components = EXCLUDED.address_components,
                quality_score = EXCLUDED.quality_score,
                province_id = EXCLUDED.province_id,
                province_name = EXCLUDED.province_name,
                district_id = EXCLUDED.district_id,
                district_name = EXCLUDED.district_name,
                ward_id = EXCLUDED.ward_id,
                ward_name = EXCLUDED.ward_name,
                updated_at = now()
            RETURNING (xmax = 0) AS inserted_flag
            """
        )

        import json

        for row in rows:
            standardized = (row["address"] or "").strip()
            if not standardized:
                skipped += 1
                continue

            components = _extract_components(
                standardized,
                row.get("province_name"),
                row.get("district_name"),
                row.get("ward_name"),
            )
            result = session.execute(
                upsert_sql,
                {
                    "standardized_address": standardized,
                    "address_components": json.dumps(components, ensure_ascii=False),
                    "source_id": row["id"],
                    "quality_score": quality_score,
                    "province_id": row.get("province_id"),
                    "province_name": row.get("province_name"),
                    "district_id": row.get("district_id"),
                    "district_name": row.get("district_name"),
                    "ward_id": row.get("ward_id"),
                    "ward_name": row.get("ward_name"),
                    "admin_epoch": admin_epoch,
                },
            ).scalar()
            if result:
                inserted += 1
            else:
                updated += 1

        session.commit()
        LOGGER.info("Migration done | inserted=%d updated=%d skipped=%d", inserted, updated, skipped)
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate prq.ground_truth to prq.address_clean_corpus")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows to migrate")
    parser.add_argument("--admin-epoch", default="2025", help="Target admin_epoch")
    parser.add_argument("--quality-score", type=float, default=1.0, help="Quality score to store")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run(limit=args.limit, admin_epoch=args.admin_epoch, quality_score=args.quality_score)


if __name__ == "__main__":
    main()
