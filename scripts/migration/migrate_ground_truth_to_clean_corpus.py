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

# Regex patterns for the five labels that the original column-based join cannot cover.
# Patterns are case-insensitive. We avoid \b because \b on Vietnamese diacritics is
# unreliable in the cp1252-friendly default; instead we anchor on (^|\s|,|\.|;) lookbehind.
_LBND = r"(?:^|(?<=[\s,.;()/-]))"

_RE_FLR = re.compile(
    _LBND + r"(?:tầng|tang|lầu|lau|floor|fl\.?)\s*([0-9]{1,2}[A-Za-z]?)",
    re.IGNORECASE,
)
_RE_RM = re.compile(
    _LBND + r"(?:phòng|phong|p\.|room|rm\.?|căn|can)\s*([0-9]+[A-Za-z]?(?:[\-\.][0-9A-Za-z]+)?)",
    re.IGNORECASE,
)
_RE_NHB = re.compile(
    _LBND + r"(?:khu phố|khu pho|kp\.?|tổ|to|ấp|ap|thôn|thon|xóm|xom)\s+([^,]+?)(?=,|$)",
    re.IGNORECASE,
)
_RE_BLD = re.compile(
    _LBND + r"(?:tòa nhà|toa nha|tòa|toa|building|block|chung cư|chung cu|cc\.?)\s+([^,]+?)(?=,|$)",
    re.IGNORECASE,
)
_RE_POI = re.compile(
    _LBND + r"(?:trường|truong|bệnh viện|benh vien|bv\.?|công viên|cong vien|"
    r"chợ|cho|siêu thị|sieu thi|trung tâm|trung tam|sân bay|san bay|"
    r"công ty|cong ty|cty\.?)\s+([^,]+?)(?=,|$)",
    re.IGNORECASE,
)


def _extract_extra_labels(addr: str) -> tuple[dict[str, Any], str]:
    """Extract FLR/RM/NHB/BLD/POI via regex.

    Returns (label_dict, residual_address) where residual_address has the matched
    fragments removed so the downstream NUM/STR pass does not pick them up.
    """
    extras: dict[str, Any] = {"FLR": None, "RM": None, "NHB": None, "BLD": None, "POI": None}
    residual = addr

    # Order matters: more specific (POI/BLD/NHB) before short tokens (FLR/RM)
    for label, pattern in (
        ("POI", _RE_POI),
        ("BLD", _RE_BLD),
        ("NHB", _RE_NHB),
        ("FLR", _RE_FLR),
        ("RM", _RE_RM),
    ):
        m = pattern.search(residual)
        if not m:
            continue
        value = m.group(1).strip(" -/.,")
        if not value:
            continue
        extras[label] = value
        # Remove the entire matched fragment to avoid leaking into STR
        residual = (residual[: m.start()] + residual[m.end() :]).strip(" ,")
    # Collapse repeated whitespace/commas left behind after stripping
    residual = re.sub(r"\s{2,}", " ", residual)
    residual = re.sub(r"\s*,\s*,+", ", ", residual)
    return extras, residual


def _extract_components(address: str | None, province: str | None, district: str | None, ward: str | None) -> dict[str, Any]:
    addr = (address or "").strip()
    prov = (province or "").strip()
    dist = (district or "").strip()
    wrd = (ward or "").strip()
    out = {k: None for k in REQUIRED_LABELS}
    if not addr:
        return out

    # 1) Extract FLR/RM/NHB/BLD/POI first; remove matched fragments from working copy
    extras, residual = _extract_extra_labels(addr)
    for k, v in extras.items():
        out[k] = v

    # 2) Extract simple house number prefix (e.g. "123", "12/5", "45A", "45A/3") from residual.
    # Allow trailing alphanumeric suffixes and slash-segments.
    num_match = re.match(r"^\s*([0-9]+[A-Za-z]?(?:/[0-9]+[A-Za-z]?)*)", residual)
    if num_match:
        out["NUM"] = num_match.group(1)

    # 3) STR is remainder before first comma after removing NUM prefix
    head = residual.split(",")[0].strip()
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
