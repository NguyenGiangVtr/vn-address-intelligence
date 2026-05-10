"""Concave-hull computation using alphashape."""
from __future__ import annotations

from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from app.tools.boundary_visualization.geometry.crs import to_metric, to_wgs84


def redraw_concave_hull(
    points: list[tuple[float, float]],
    alpha: float = 0.3,
    metric_epsg: int = 32648,
    min_points: int = 4,
) -> BaseGeometry | None:
    """
    Compute a concave hull of (lat, lng) points using alphashape.

    Returns a WGS-84 geometry or None when not enough points.
    """
    if len(points) < min_points:
        return None

    import alphashape
    from shapely.geometry import Point

    # Convert to metric (x, y) tuples
    metric_pts = []
    for lat, lng in points:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", f"EPSG:{metric_epsg}", always_xy=True)
        x, y = t.transform(lng, lat)
        metric_pts.append((x, y))

    try:
        hull_m = alphashape.alphashape(metric_pts, alpha)
        if hull_m is None or hull_m.is_empty:
            return None
        return to_wgs84(hull_m, metric_epsg)
    except Exception:
        return None
