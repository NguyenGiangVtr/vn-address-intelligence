"""
edge_inject.py
==============
Chiến lược 3: Edge Inject Correction (G3 — Spatial Mismatch)

Khi điểm GPS nằm sát biên hai đơn vị hành chính (ví dụ: cùng đường biên
giữa hai phường), sử dụng đồ thị quan hệ hành chính (mat.unit_edge) kết hợp
khoảng cách đến centroid để chọn đơn vị phù hợp hơn.

Không yêu cầu PostGIS — chỉ cần lat/lon centroid trong DB.
"""

from __future__ import annotations

import logging
import math
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách Haversine giữa hai điểm (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def edge_inject_lookup(
    db_session,
    lat: float,
    lon: float,
    candidate_unit_id: int,
    unit_level: str = "ward",
    radius_km: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """
    Cải chính biên giới bằng đồ thị unit_edge.

    Thuật toán:
    1. Lấy các đơn vị liên kết với candidate_unit_id qua mat.unit_edge
    2. Tính khoảng cách Haversine từ điểm GPS đến centroid mỗi đơn vị
    3. Trả về đơn vị gần nhất trong bán kính radius_km

    Parameters
    ----------
    db_session        : SQLAlchemy Session
    lat, lon          : Tọa độ GPS cần kiểm tra
    candidate_unit_id : Đơn vị hành chính ban đầu (từ Point-in-Polygon hoặc nearest)
    unit_level        : 'province' | 'district' | 'ward'
    radius_km         : Bán kính tìm kiếm (km)
    """
    from sqlalchemy import text

    level_table_map = {
        "ward":     ("mat.ward",     "ward_id",     "north_pole_lat", "north_pole_lng"),
        "district": ("mat.district", "district_id", None, None),
        "province": ("mat.province", "province_id", "north_pole_lat", "north_pole_lng"),
    }
    if unit_level not in level_table_map:
        return None

    tbl, id_col, lat_col, lon_col = level_table_map[unit_level]

    # Ward và District không có centroid columns — fallback về Area Polygon
    if not lat_col:
        return _edge_inject_via_area_polygon(
            db_session, lat, lon, candidate_unit_id, unit_level, radius_km
        )

    neighbors_sql = text(f"""
        SELECT ue.to_unit_id
        FROM mat.unit_edge ue
        WHERE ue.from_unit_id = :uid AND ue.from_level = :level
        UNION
        SELECT ue.from_unit_id
        FROM mat.unit_edge ue
        WHERE ue.to_unit_id = :uid AND ue.to_level = :level
    """)

    neighbor_ids_rows = db_session.execute(
        neighbors_sql, {"uid": candidate_unit_id, "level": unit_level}
    ).fetchall()

    candidate_ids = {candidate_unit_id} | {r[0] for r in neighbor_ids_rows}

    candidates_sql = text(f"""
        SELECT {id_col}, {lat_col}, {lon_col}
        FROM {tbl}
        WHERE {id_col} = ANY(:ids)
          AND is_current = TRUE
          AND {lat_col} IS NOT NULL
    """)

    try:
        rows = db_session.execute(
            candidates_sql, {"ids": list(candidate_ids)}
        ).fetchall()
    except Exception as exc:
        logger.error("edge_inject_lookup query error: %s", exc)
        return None

    best_unit_id  = None
    best_dist_km  = float("inf")

    for r in rows:
        uid, c_lat, c_lon = r
        if c_lat is None or c_lon is None:
            continue
        dist = _haversine_km(lat, lon, float(c_lat), float(c_lon))
        if dist < best_dist_km and dist <= radius_km:
            best_dist_km = dist
            best_unit_id = uid

    if best_unit_id is None:
        return None

    return {
        "unit_id":    best_unit_id,
        "method":     "edge_inject",
        "distance_km": round(best_dist_km, 4),
    }


def _edge_inject_via_area_polygon(
    db_session,
    lat: float,
    lon: float,
    candidate_unit_id: int,
    unit_level: str,
    radius_km: float,
) -> Optional[Dict[str, Any]]:
    """Fallback edge inject dùng centroid từ mat.area_polygon."""
    from sqlalchemy import text

    neighbors_sql = text("""
        SELECT ue.to_unit_id, ue.to_level
        FROM mat.unit_edge ue
        WHERE ue.from_unit_id = :uid AND ue.from_level = :level
        UNION
        SELECT ue.from_unit_id, ue.from_level
        FROM mat.unit_edge ue
        WHERE ue.to_unit_id = :uid AND ue.to_level = :level
    """)
    neighbor_rows = db_session.execute(
        neighbors_sql, {"uid": candidate_unit_id, "level": unit_level}
    ).fetchall()
    candidate_ids = [candidate_unit_id] + [r[0] for r in neighbor_rows]

    try:
        polygon_sql = text("""
            SELECT unit_id, unit_name, geojson
            FROM mat.area_polygon
            WHERE unit_level = :level AND unit_id = ANY(:ids)
        """)
        poly_rows = db_session.execute(
            polygon_sql, {"level": unit_level, "ids": candidate_ids}
        ).fetchall()
    except Exception as exc:
        logger.error("_edge_inject_via_area_polygon error: %s", exc)
        return None

    import json

    best_unit_id   = None
    best_unit_name = None
    best_dist_km   = float("inf")

    for row in poly_rows:
        uid, uname, geojson_val = row
        try:
            geom = json.loads(geojson_val) if isinstance(geojson_val, str) else geojson_val
            coords = _extract_coords(geom)
            if not coords:
                continue
            c_lat = sum(c[1] for c in coords) / len(coords)
            c_lon = sum(c[0] for c in coords) / len(coords)
            dist = _haversine_km(lat, lon, c_lat, c_lon)
            if dist < best_dist_km and dist <= radius_km:
                best_dist_km   = dist
                best_unit_id   = uid
                best_unit_name = uname
        except Exception:
            continue

    if best_unit_id is None:
        return None

    return {
        "unit_id":    best_unit_id,
        "unit_name":  best_unit_name,
        "method":     "edge_inject",
        "distance_km": round(best_dist_km, 4),
    }


def _extract_coords(geom: dict) -> List:
    """Lấy danh sách [lon, lat] từ GeoJSON geometry."""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if gtype == "Point":
        return [coords]
    if gtype in ("MultiPoint", "LineString"):
        return coords
    if gtype in ("Polygon", "MultiLineString"):
        return [c for ring in coords for c in ring]
    if gtype == "MultiPolygon":
        return [c for poly in coords for ring in poly for c in ring]
    return []
