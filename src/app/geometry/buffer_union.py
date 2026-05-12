"""
buffer_union.py
===============
Chiến lược 1: Buffer Union Correction (G3 — Spatial Mismatch)

Khi một điểm GPS nằm gần biên ranh giới nhưng lại rơi ra ngoài polygon
(do sai số GPS hoặc polygon không chính xác), chiến lược Buffer Union
mở rộng polygon một khoảng nhỏ (buffer) rồi kiểm tra lại.

Yêu cầu PostGIS hoặc shapely.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Bán kính buffer mặc định (độ thập phân ≈ ~50m tại vĩ độ Việt Nam)
DEFAULT_BUFFER_DEGREES = 0.0005   # ~55m
MAX_BUFFER_DEGREES     = 0.005    # ~550m


def buffer_union_lookup(
    db_session,
    lat: float,
    lon: float,
    unit_level: str = "ward",
    buffer_degrees: float = DEFAULT_BUFFER_DEGREES,
) -> Optional[Dict[str, Any]]:
    """
    Tìm đơn vị hành chính bằng cách mở rộng polygon với ST_Buffer.

    Parameters
    ----------
    db_session   : SQLAlchemy Session (có PostGIS)
    lat, lon     : Tọa độ GPS cần kiểm tra
    unit_level   : 'province' | 'district' | 'ward'
    buffer_degrees: Khoảng mở rộng (độ)

    Returns
    -------
    Dict với unit_id, unit_name, buffer_used hoặc None nếu không tìm thấy.
    """
    from sqlalchemy import text

    sql = text("""
        SELECT unit_id, unit_name
        FROM mat.area_polygon
        WHERE unit_level = :level
          AND ST_Contains(
              ST_Buffer(
                  ST_SetSRID(ST_GeomFromGeoJSON(geojson::text), 4326),
                  :buf
              ),
              ST_SetSRID(ST_Point(:lon, :lat), 4326)
          )
        ORDER BY
            ST_Distance(
                ST_SetSRID(ST_Centroid(ST_GeomFromGeoJSON(geojson::text)), 4326),
                ST_SetSRID(ST_Point(:lon, :lat), 4326)
            ) ASC
        LIMIT 1
    """)

    try:
        row = db_session.execute(
            sql,
            {"level": unit_level, "lat": lat, "lon": lon, "buf": buffer_degrees},
        ).fetchone()
        if row:
            return {
                "unit_id":    row[0],
                "unit_name":  row[1],
                "method":     "buffer_union",
                "buffer_deg": buffer_degrees,
            }
    except Exception as exc:
        logger.error("buffer_union_lookup error: %s", exc)

    return None


def adaptive_buffer_lookup(
    db_session,
    lat: float,
    lon: float,
    unit_level: str = "ward",
) -> Optional[Dict[str, Any]]:
    """
    Thử buffer với khoảng tăng dần (50m → 150m → 550m) cho đến khi tìm được.
    """
    buffers = [DEFAULT_BUFFER_DEGREES, DEFAULT_BUFFER_DEGREES * 3, MAX_BUFFER_DEGREES]
    for buf in buffers:
        result = buffer_union_lookup(db_session, lat, lon, unit_level, buf)
        if result:
            return result
    return None
