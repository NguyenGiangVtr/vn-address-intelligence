"""Expand a base polygon to cover outlier points via buffer-then-union."""
from __future__ import annotations

from shapely.geometry import Point, MultiPoint
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from app.tools.boundary_visualization.geometry.crs import to_metric, to_wgs84


def expand_buffer_union(
    base_polygon: BaseGeometry,
    outlier_points: list[tuple[float, float]],
    buffer_m: float = 50.0,
    metric_epsg: int = 32648,
) -> BaseGeometry:
    """
    Return a new polygon that covers base_polygon plus all outlier_points.

    Strategy:
    1. Project everything to metric CRS.
    2. Buffer each outlier point by buffer_m metres.
    3. Union the base polygon with all buffered point blobs.
    4. Project result back to WGS-84.
    """
    if not outlier_points:
        return base_polygon

    base_m = to_metric(base_polygon, metric_epsg)

    blobs = [to_metric(Point(lng, lat), metric_epsg).buffer(buffer_m)
             for lat, lng in outlier_points]

    expanded_m = unary_union([base_m] + blobs)
    return to_wgs84(expanded_m, metric_epsg)
