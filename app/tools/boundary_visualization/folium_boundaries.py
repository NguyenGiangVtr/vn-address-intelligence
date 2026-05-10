import json

import folium


def _partner_color(partner_name):
    palette = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]
    key = (partner_name or "unknown").strip().lower()
    return palette[hash(key) % len(palette)]


def _partner_layer_name(partner_name):
    normalized = (partner_name or "").strip()
    return f"Partner: {normalized}" if normalized else "Partner: unknown"


def _normalize_lat_lng_pair(value):
    if isinstance(value, dict):
        lat = value.get("lat", value.get("latitude"))
        lng = value.get("lng", value.get("lon", value.get("longitude")))
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            return [float(lat), float(lng)]
        return None

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        first, second = value[0], value[1]
        if not isinstance(first, (int, float)) or not isinstance(second, (int, float)):
            return None
        if -90 <= first <= 90 and -180 <= second <= 180:
            return [float(first), float(second)]
        if -180 <= first <= 180 and -90 <= second <= 90:
            return [float(second), float(first)]
        return [float(first), float(second)]
    return None


def _extract_polygon_rings(raw_coordinates):
    def walk(node):
        if node is None:
            return []
        if isinstance(node, str):
            try:
                return walk(json.loads(node))
            except Exception:
                return []
        if isinstance(node, dict):
            geo_type = str(node.get("type", "")).lower()
            coords = node.get("coordinates")
            if geo_type in ("polygon", "multipolygon") and coords is not None:
                return walk(coords)
            if coords is not None:
                return walk(coords)
            return []
        if not isinstance(node, (list, tuple)) or not node:
            return []

        if _normalize_lat_lng_pair(node[0]) is not None:
            ring = []
            for point in node:
                normalized = _normalize_lat_lng_pair(point)
                if normalized is not None:
                    ring.append(normalized)
            return [ring] if len(ring) >= 3 else []

        rings = []
        for child in node:
            rings.extend(walk(child))
        return rings

    return walk(raw_coordinates)


def extract_polygon_rings(raw_coordinates):
    return _extract_polygon_rings(raw_coordinates)


def add_boundaries_to_map(map_obj, polygons, *, fixed_color=None, fill_opacity=0.12):
    """
    Render polygon rings onto map_obj.

    fixed_color: when set, all rings are drawn in that single colour with no
                 partner-based layer grouping (used by audit/mismatch tools).
    fill_opacity: fill opacity when fixed_color is active (default 0.12).
    """
    if fixed_color is not None:
        total_rings = 0
        layer = folium.FeatureGroup(name="Boundaries", show=True)
        layer.add_to(map_obj)
        for polygon in polygons:
            rings = _extract_polygon_rings(polygon.get("coordinates"))
            for ring in rings:
                total_rings += 1
                folium.Polygon(
                    locations=ring,
                    color=fixed_color,
                    weight=2,
                    fill=True,
                    fill_color=fixed_color,
                    fill_opacity=fill_opacity,
                    popup=f"Area: {polygon.get('area_name') or polygon.get('unit_name') or 'N/A'}",
                ).add_to(layer)
        return total_rings

    partner_layers = {}
    total_rings = 0
    for polygon in polygons:
        partner_name = polygon.get("partner_name")
        polygon_color = _partner_color(partner_name)
        layer_name = _partner_layer_name(partner_name)
        if layer_name not in partner_layers:
            partner_layers[layer_name] = folium.FeatureGroup(name=layer_name, show=True)
            partner_layers[layer_name].add_to(map_obj)

        rings = _extract_polygon_rings(polygon.get("coordinates"))
        for ring in rings:
            total_rings += 1
            folium.Polygon(
                locations=ring,
                color=polygon_color,
                weight=2,
                fill=True,
                fill_color=polygon_color,
                fill_opacity=0.08,
                popup=(
                    f"Area: {polygon.get('area_name') or 'N/A'}"
                    f" | Partner: {partner_name or 'unknown'}"
                    f" | Polygon ID: {polygon.get('area_polygon_id')}"
                ),
            ).add_to(partner_layers[layer_name])
    return total_rings
