from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional

from app.tools.boundary_visualization.folium_boundaries import add_boundaries_to_map, extract_polygon_rings
from app.tools.boundary_visualization.load_polygons import fetch_area_polygons
import folium

router = APIRouter()
logger = logging.getLogger("VNAI_BoundaryAPI")


@router.get("/map", tags=["Bản đồ địa giới"], summary="Tạo bản đồ ranh giới hành chính")
def generate_boundary_map(
    scope: str = Query("province", pattern="^(province|district|ward)$"),
    province_id: Optional[int] = None,
    district_id: Optional[int] = None,
    ward_id: Optional[int] = None,
    zoom_start: int = 11,
):
    """
    Tạo một bản đồ Folium hiển thị ranh giới của Tỉnh, Huyện hoặc Xã.
    Trả về URL của tệp HTML bản đồ đã được tạo.
    """
    try:
        polygons = fetch_area_polygons(scope=scope, province_id=province_id, district_id=district_id, ward_id=ward_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # Graceful fallback for local/dev databases that do not have mat.area_polygon yet.
        logger.warning("Boundary polygon fetch failed, fallback to empty map: %s", exc)
        polygons = []

    # determine map center
    def _map_center(polygons):
        lats = []
        lngs = []
        for polygon in polygons:
            rings = extract_polygon_rings(polygon.get("coordinates"))
            for ring in rings:
                for lat, lng in ring:
                    lats.append(lat)
                    lngs.append(lng)
        if lats and lngs:
            return [sum(lats) / len(lats), sum(lngs) / len(lngs)]
        return [10.762622, 106.660172]

    center = _map_center(polygons)
    boundary_map = folium.Map(location=center, zoom_start=zoom_start, prefer_canvas=True)
    ring_count = add_boundaries_to_map(boundary_map, polygons)
    folium.LayerControl(collapsed=False).add_to(boundary_map)

    # Save under ui/pages/generated (served via /pages by StaticFiles on ui/pages)
    pages_dir = Path("ui/pages/generated")
    pages_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"boundary_map_{scope}_{timestamp}.html"
    output_path = pages_dir / filename
    boundary_map.save(str(output_path))

    return {"url": f"/pages/generated/{filename}", "rings": ring_count}
