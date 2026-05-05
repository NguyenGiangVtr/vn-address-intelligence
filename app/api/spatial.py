"""
spatial.py
==========
Spatial API Router — Geospatial Point-in-Polygon và Mismatch Analysis (G3, Chương 2.5, 3.4)

Endpoints:
    POST /api/spatial/subdivide   — Point-in-Polygon batch với fallback ST_Distance nearest
    GET  /api/spatial/mismatch-report — Mismatch analysis report
"""

from __future__ import annotations

import logging
import json
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spatial", tags=["Spatial / GIS"])


# ── Dependency ─────────────────────────────────────────────────────────────────

def get_db():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schemas ───────────────────────────────────────────────────────────────────

class PointInput(BaseModel):
    lat: float
    lon: float
    order_id: Optional[str] = None


class SubdivideRequest(BaseModel):
    points: List[PointInput]
    level: str = "ward"  # province | district | ward


class SubdivideResult(BaseModel):
    order_id: Optional[str]
    lat: float
    lon: float
    unit_id: Optional[int]
    unit_name: Optional[str]
    match_method: str  # polygon | nearest | none


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_postgis(db: Session) -> bool:
    """Kiểm tra PostGIS extension đã cài chưa."""
    try:
        result = db.execute(
            text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'postgis'")
        ).scalar()
        return (result or 0) > 0
    except Exception:
        return False


def _point_in_polygon_query(db: Session, lat: float, lon: float, level: str) -> Optional[Dict]:
    """
    Tìm đơn vị hành chính chứa điểm (lat, lon) bằng ST_Contains.
    Yêu cầu PostGIS + geometry column trong mat.area_polygon.
    """
    try:
        sql = text("""
            SELECT unit_id, unit_name
            FROM mat.area_polygon
            WHERE unit_level = :level
              AND ST_Contains(
                  ST_SetSRID(ST_GeomFromGeoJSON(geojson::text), 4326),
                  ST_SetSRID(ST_Point(:lon, :lat), 4326)
              )
            LIMIT 1
        """)
        row = db.execute(sql, {"level": level, "lat": lat, "lon": lon}).fetchone()
        if row:
            return {"unit_id": row[0], "unit_name": row[1], "method": "polygon"}
    except Exception as exc:
        logger.warning("ST_Contains failed: %s", exc)
    return None


def _nearest_unit_query(db: Session, lat: float, lon: float, level: str) -> Optional[Dict]:
    """
    Fallback: tìm đơn vị gần nhất theo ST_Distance (centroid).
    """
    try:
        sql = text("""
            SELECT unit_id, unit_name,
                   ST_Distance(
                       ST_SetSRID(ST_Centroid(ST_GeomFromGeoJSON(geojson::text)), 4326),
                       ST_SetSRID(ST_Point(:lon, :lat), 4326)
                   ) AS dist
            FROM mat.area_polygon
            WHERE unit_level = :level
            ORDER BY dist ASC
            LIMIT 1
        """)
        row = db.execute(sql, {"level": level, "lat": lat, "lon": lon}).fetchone()
        if row:
            return {"unit_id": row[0], "unit_name": row[1], "method": "nearest"}
    except Exception as exc:
        logger.warning("ST_Distance fallback failed: %s", exc)
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/subdivide",
    summary="Point-in-Polygon batch — Xác định đơn vị hành chính từ tọa độ GPS",
    response_model=Dict[str, Any],
)
def spatial_subdivide(
    request: SubdivideRequest,
    db: Session = Depends(get_db),
):
    """
    Nhận danh sách tọa độ GPS (lat, lon) và trả về đơn vị hành chính tương ứng.

    Chiến lược:
    1. ST_Contains — Point-in-Polygon chính xác
    2. ST_Distance nearest — Fallback khi điểm nằm ngoài polygon (vùng biên)

    Yêu cầu PostGIS extension và dữ liệu trong `mat.area_polygon`.
    """
    if request.level not in ("province", "district", "ward"):
        raise HTTPException(
            status_code=400,
            detail="level phải là: province, district, ward",
        )

    has_postgis = _check_postgis(db)

    results: List[SubdivideResult] = []
    polygon_hits = 0
    nearest_hits = 0
    no_match     = 0

    for pt in request.points:
        matched = None

        if has_postgis:
            matched = _point_in_polygon_query(db, pt.lat, pt.lon, request.level)
            if matched:
                polygon_hits += 1

        if not matched and has_postgis:
            matched = _nearest_unit_query(db, pt.lat, pt.lon, request.level)
            if matched:
                nearest_hits += 1

        if not matched:
            no_match += 1

        results.append(
            SubdivideResult(
                order_id=pt.order_id,
                lat=pt.lat,
                lon=pt.lon,
                unit_id=matched["unit_id"] if matched else None,
                unit_name=matched["unit_name"] if matched else None,
                match_method=matched["method"] if matched else "none",
            )
        )

    return {
        "total": len(results),
        "level": request.level,
        "postgis_available": has_postgis,
        "stats": {
            "polygon_match": polygon_hits,
            "nearest_match": nearest_hits,
            "no_match": no_match,
        },
        "results": [r.model_dump() for r in results],
    }


@router.get(
    "/mismatch-report",
    summary="Báo cáo phân tích sai lệch địa lý (Spatial Mismatch)",
)
def get_mismatch_report(
    province_id: Optional[int] = Query(None, description="Lọc theo tỉnh thành"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Báo cáo các địa chỉ trong `prq.address_cleansing_queue` có tọa độ GPS
    không khớp với đơn vị hành chính được gán (mismatch giữa lat/lon và ward_id).

    Yêu cầu PostGIS và dữ liệu `mat.area_polygon`.
    """
    has_postgis = _check_postgis(db)
    if not has_postgis:
        return {
            "status": "warning",
            "message": "PostGIS chưa được cài đặt. Cài đặt với: CREATE EXTENSION IF NOT EXISTS postgis;",
            "mismatches": [],
        }

    try:
        sql = text("""
            SELECT
                q.id,
                q.raw_address,
                q.latitude,
                q.longitude,
                q.ward_id AS declared_ward_id,
                q.ward_name AS declared_ward_name,
                ap.unit_id AS gps_ward_id,
                ap.unit_name AS gps_ward_name
            FROM prq.address_cleansing_queue q
            JOIN mat.area_polygon ap ON (
                ap.unit_level = 'ward'
                AND ST_Contains(
                    ST_SetSRID(ST_GeomFromGeoJSON(ap.geojson::text), 4326),
                    ST_SetSRID(ST_Point(q.longitude::float, q.latitude::float), 4326)
                )
            )
            WHERE q.latitude IS NOT NULL
              AND q.longitude IS NOT NULL
              AND q.ward_id IS NOT NULL
              AND ap.unit_id != q.ward_id
              AND (:province_id IS NULL OR q.province_id = :province_id)
            ORDER BY q.id DESC
            LIMIT :limit
        """)
        rows = db.execute(sql, {"province_id": province_id, "limit": limit}).fetchall()

        mismatches = [
            {
                "id": r[0],
                "raw_address": r[1],
                "lat": float(r[2]) if r[2] else None,
                "lon": float(r[3]) if r[3] else None,
                "declared_ward_id": r[4],
                "declared_ward_name": r[5],
                "gps_ward_id": r[6],
                "gps_ward_name": r[7],
            }
            for r in rows
        ]

        return {
            "status": "ok",
            "total_mismatches": len(mismatches),
            "province_filter": province_id,
            "mismatches": mismatches,
        }

    except Exception as exc:
        logger.error("Mismatch report error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi tìm kiếm spatial: {exc}")


@router.get(
    "/postgis-status",
    summary="Kiểm tra trạng thái PostGIS extension",
)
def check_postgis_status(db: Session = Depends(get_db)):
    """Xác nhận PostGIS extension đã được cài đặt chưa."""
    installed = _check_postgis(db)
    try:
        version_row = db.execute(text("SELECT PostGIS_Version()")).scalar() if installed else None
    except Exception:
        version_row = None

    polygon_count = 0
    if installed:
        try:
            polygon_count = db.execute(
                text("SELECT COUNT(*) FROM mat.area_polygon")
            ).scalar() or 0
        except Exception:
            polygon_count = 0

    return {
        "postgis_installed": installed,
        "postgis_version": version_row,
        "area_polygon_count": polygon_count,
        "advice": (
            "PostGIS đã sẵn sàng."
            if installed
            else "Chưa cài PostGIS. Chạy: CREATE EXTENSION IF NOT EXISTS postgis;"
        ),
    }
