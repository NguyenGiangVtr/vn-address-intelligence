"""Coordinate-reference-system helpers using pyproj.

Uses EPSG:32648 (UTM zone 48N) for metric-unit calculations over Vietnam.
"""
from __future__ import annotations

from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


_CACHE: dict[tuple[int, int], Transformer] = {}


def _get_transformer(src_epsg: int, dst_epsg: int) -> Transformer:
    key = (src_epsg, dst_epsg)
    if key not in _CACHE:
        _CACHE[key] = Transformer.from_crs(
            f"EPSG:{src_epsg}", f"EPSG:{dst_epsg}", always_xy=True
        )
    return _CACHE[key]


def to_metric(geom: BaseGeometry, metric_epsg: int = 32648) -> BaseGeometry:
    """Project WGS-84 geometry to a metric CRS (default UTM 48N)."""
    t = _get_transformer(4326, metric_epsg)
    return transform(t.transform, geom)


def to_wgs84(geom: BaseGeometry, metric_epsg: int = 32648) -> BaseGeometry:
    """Project metric geometry back to WGS-84."""
    t = _get_transformer(metric_epsg, 4326)
    return transform(t.transform, geom)
