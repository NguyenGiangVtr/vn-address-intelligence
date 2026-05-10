"""
concave_hull.py
===============
Chiến lược 2: Concave Hull từ đám mây điểm (G3 — Spatial Mismatch)

Khi polygon trong DB không chính xác, tái tạo polygon từ đám mây điểm
(các địa chỉ đã biết thuộc đơn vị đó) bằng Concave Hull.

Yêu cầu PostGIS (ST_ConcaveHull) hoặc scipy + shapely.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def build_concave_hull_from_points(
    db_session,
    unit_id: int,
    unit_level: str = "ward",
    target_percent: float = 0.95,
) -> Optional[Dict[str, Any]]:
    """
    Tạo Concave Hull từ các điểm GPS đã biết thuộc đơn vị hành chính.

    Parameters
    ----------
    db_session     : SQLAlchemy Session (có PostGIS)
    unit_id        : ID đơn vị cần tái tạo polygon
    unit_level     : 'province' | 'district' | 'ward'
    target_percent : Tham số ST_ConcaveHull [0..1], gần 1 = convex hull

    Returns
    -------
    Dict với 'geojson' (GeoJSON string), 'point_count' hoặc None nếu thất bại.
    """
    from sqlalchemy import text

    # Matches denormalised queue FK columns (`ward_id`/`district_id`/`province_id`).
    # Administrative *semantic* resolution from queue ↔ mat uses lineage `old_*` → mat.old_id
    # (`admin_version = 1`) — see `app/domain/acq_mat_lineage.py`.
    level_col_map = {
        "ward":     ("ward_id",     "prq.address_cleansing_queue"),
        "district": ("district_id", "prq.address_cleansing_queue"),
        "province": ("province_id", "prq.address_cleansing_queue"),
    }

    if unit_level not in level_col_map:
        logger.error("unit_level không hợp lệ: %s", unit_level)
        return None

    id_col, table = level_col_map[unit_level]

    count_sql = text(f"""
        SELECT COUNT(*) FROM {table}
        WHERE {id_col} = :unit_id
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
    """)
    count = db_session.execute(count_sql, {"unit_id": unit_id}).scalar() or 0

    if count < 3:
        logger.warning(
            "Không đủ điểm để tạo Concave Hull cho %s %d (chỉ có %d điểm)",
            unit_level, unit_id, count,
        )
        return None

    hull_sql = text(f"""
        SELECT ST_AsGeoJSON(
            ST_ConcaveHull(
                ST_Collect(
                    ST_SetSRID(ST_Point(longitude::float, latitude::float), 4326)
                ),
                :target_percent
            )
        ) AS hull_geojson
        FROM {table}
        WHERE {id_col} = :unit_id
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
    """)

    try:
        row = db_session.execute(
            hull_sql,
            {"unit_id": unit_id, "target_percent": target_percent},
        ).fetchone()
        if row and row[0]:
            return {
                "geojson":      row[0],
                "point_count":  count,
                "method":       "concave_hull",
                "target_percent": target_percent,
            }
    except Exception as exc:
        logger.error("ST_ConcaveHull failed: %s", exc)

    return None


def upsert_hull_to_area_polygon(
    db_session,
    unit_id: int,
    unit_level: str,
    unit_name: str,
    geojson_str: str,
    source: str = "CONCAVE_HULL",
) -> bool:
    """
    Lưu hoặc cập nhật polygon đã tính vào mat.area_polygon.
    """
    import json
    from sqlalchemy import text
    try:
        geojson_obj = json.loads(geojson_str)
        existing = db_session.execute(
            text("""
                SELECT id FROM mat.area_polygon
                WHERE unit_level = :level AND unit_id = :unit_id
                LIMIT 1
            """),
            {"level": unit_level, "unit_id": unit_id},
        ).fetchone()

        if existing:
            db_session.execute(
                text("""
                    UPDATE mat.area_polygon
                    SET geojson = :geojson, source = :source, updated_at = NOW()
                    WHERE unit_level = :level AND unit_id = :unit_id
                """),
                {
                    "geojson": json.dumps(geojson_obj),
                    "source": source,
                    "level": unit_level,
                    "unit_id": unit_id,
                },
            )
        else:
            db_session.execute(
                text("""
                    INSERT INTO mat.area_polygon (unit_level, unit_id, unit_name, geojson, source)
                    VALUES (:level, :unit_id, :unit_name, :geojson, :source)
                """),
                {
                    "level": unit_level,
                    "unit_id": unit_id,
                    "unit_name": unit_name,
                    "geojson": json.dumps(geojson_obj),
                    "source": source,
                },
            )

        db_session.commit()
        return True
    except Exception as exc:
        logger.error("upsert_hull_to_area_polygon error: %s", exc)
        db_session.rollback()
        return False
