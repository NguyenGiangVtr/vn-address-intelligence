"""Inject outlier points as vertices into the nearest polygon edge."""
from __future__ import annotations

import math

from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry

from app.tools.boundary_visualization.geometry.crs import to_metric, to_wgs84


def _nearest_edge_insert(ring: list[tuple], pt_m) -> list[tuple]:
    """Insert pt_m into ring at the position that minimises insertion distance."""
    best_idx = 0
    best_dist = math.inf
    px, py = pt_m.x, pt_m.y

    for i in range(len(ring) - 1):
        ax, ay = ring[i]
        bx, by = ring[i + 1]
        # Foot of perpendicular
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
        fx, fy = ax + t * dx, ay + t * dy
        dist = math.hypot(px - fx, py - fy)
        if dist < best_dist:
            best_dist = dist
            best_idx = i + 1

    new_ring = list(ring)
    new_ring.insert(best_idx, (pt_m.x, pt_m.y))
    return new_ring


def inject_outlier_vertices(
    base_polygon: BaseGeometry,
    outlier_points: list[tuple[float, float]],
    metric_epsg: int = 32648,
) -> BaseGeometry:
    """
    Return a new polygon where each outlier point is injected into the nearest
    edge of the exterior ring.
    """
    if not outlier_points:
        return base_polygon

    # Work with first polygon if MultiPolygon
    poly = base_polygon
    if isinstance(poly, MultiPolygon):
        poly = max(poly.geoms, key=lambda g: g.area)

    poly_m = to_metric(poly, metric_epsg)
    ring = list(poly_m.exterior.coords)

    for lat, lng in outlier_points:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", f"EPSG:{metric_epsg}", always_xy=True)
        x, y = t.transform(lng, lat)
        pt_m = Point(x, y)
        ring = _nearest_edge_insert(ring, pt_m)

    new_poly_m = Polygon(ring)
    return to_wgs84(new_poly_m, metric_epsg)
