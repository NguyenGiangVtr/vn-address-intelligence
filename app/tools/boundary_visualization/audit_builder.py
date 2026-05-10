"""Cannot-determine audit map builder.

Generates a self-contained interactive HTML for reviewing orders that could
not be definitively assigned to a ward. Shows:
  - Order point on map
  - Adjacent ward polygons from DB
  - Geometry method previews: buffer-union, concave-hull, edge-inject
  - Determination buttons (indeterminate / csv_correct / api_correct)
  - Decisions saved to localStorage under ccmap_audit_cannot_determine_decisions
"""
from __future__ import annotations

import json
import logging
from typing import Any

import folium
from branca.element import Element
from shapely.geometry import Point, shape

from app.core.database import engine
from app.tools.boundary_visualization.folium_boundaries import extract_polygon_rings
from app.tools.boundary_visualization.load_polygons import fetch_area_polygons

logger = logging.getLogger(__name__)


# ── Polygon / DB helpers ───────────────────────────────────────────────────────

def _fetch_nearby_ward_polygons(lat: float, lng: float, radius_degrees: float = 0.05) -> list[dict]:
    """Fetch ward polygons from area_polygon within a bounding box around the point."""
    try:
        from sqlalchemy import text
        sql = text("""
            SELECT area_polygon_id, area_name, ward_id, coordinates
            FROM mat.area_polygon
            WHERE ward_id IS NOT NULL
              AND COALESCE(is_deleted, false) = false
            LIMIT 20
        """)
        with engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(sql)]
        return rows
    except Exception as exc:
        logger.debug("area_polygon query failed: %s", exc)
        return []


def _rings_to_geojson_coords(rings: list[list]) -> list:
    """Convert ring list to GeoJSON-ready coordinate list (swap lat/lng to lng/lat)."""
    return [[[pt[1], pt[0]] for pt in ring] for ring in rings]


def _compute_geometry_previews(
    base_rings: list[list],
    outlier_points: list[tuple],
    *,
    buffer_m: float,
    alpha: float,
    max_neighbors: int,
) -> dict[str, Any]:
    """Compute buffer_union, concave_hull, edge_inject previews. Returns ring lists."""
    previews: dict[str, Any] = {
        "buffer_union": None,
        "concave_hull": None,
        "edge_inject":  None,
    }
    if not base_rings or not outlier_points:
        return previews

    try:
        from shapely.geometry import Polygon as SPoly
        from app.tools.boundary_visualization.geometry import (
            expand_buffer_union, redraw_concave_hull, inject_outlier_vertices,
        )

        coords = [(pt[1], pt[0]) for pt in base_rings[0]]   # lng,lat → shapely
        base_poly = SPoly(coords)
        if not base_poly.is_valid:
            base_poly = base_poly.buffer(0)

        pts = outlier_points[:max_neighbors]

        # Buffer-union
        bu = expand_buffer_union(base_poly, pts, buffer_m=buffer_m)
        if bu and not bu.is_empty:
            ext = list(bu.exterior.coords) if hasattr(bu, 'exterior') else []
            previews["buffer_union"] = [[[c[1], c[0]] for c in ext]] if ext else None

        # Concave hull
        all_pts = [(pt[0], pt[1]) for pt in pts]
        ch = redraw_concave_hull(all_pts, alpha=alpha)
        if ch and not ch.is_empty:
            ext = list(ch.exterior.coords) if hasattr(ch, 'exterior') else []
            previews["concave_hull"] = [[[c[1], c[0]] for c in ext]] if ext else None

        # Edge inject
        ei = inject_outlier_vertices(base_poly, pts)
        if ei and not ei.is_empty:
            ext = list(ei.exterior.coords) if hasattr(ei, 'exterior') else []
            previews["edge_inject"] = [[[c[1], c[0]] for c in ext]] if ext else None

    except Exception as exc:
        logger.warning("Geometry preview failed: %s", exc)

    return previews


# ── Record assembler ───────────────────────────────────────────────────────────

def _build_audit_records(
    rows: list[dict],
    *,
    buffer_m: float,
    alpha: float,
    max_neighbors: int,
    limit: int,
) -> list[dict]:
    records: list[dict] = []
    process_rows = rows[:limit] if limit > 0 else rows

    for row in process_rows:
        try:
            lat = float(row.get("lat") or 0)
            lng = float(row.get("lng") or 0)
        except (TypeError, ValueError):
            continue

        csv_ward  = _safe_int(row.get("csv_ward_id"))
        api_ward  = _safe_int(row.get("api_ward_id"))
        order_code = row.get("order_code", "")

        # Fetch polygons for CSV and API ward
        csv_polys = _safe_fetch_ward(csv_ward)
        api_polys = _safe_fetch_ward(api_ward)

        csv_rings = []
        for p in csv_polys:
            csv_rings.extend(extract_polygon_rings(p.get("coordinates")))
        api_rings = []
        for p in api_polys:
            api_rings.extend(extract_polygon_rings(p.get("coordinates")))

        base_rings = csv_rings or api_rings
        outlier_points = [(lat, lng)]

        geo_previews = _compute_geometry_previews(
            base_rings, outlier_points,
            buffer_m=buffer_m, alpha=alpha, max_neighbors=max_neighbors,
        )

        records.append({
            "order_code":  order_code,
            "lat":         lat,
            "lng":         lng,
            "csv_ward_id": csv_ward,
            "api_ward_id": api_ward,
            "determination": row.get("determination", "indeterminate"),
            "csv_rings":   csv_rings,
            "api_rings":   api_rings,
            "geo_buffer_union":  geo_previews["buffer_union"],
            "geo_concave_hull":  geo_previews["concave_hull"],
            "geo_edge_inject":   geo_previews["edge_inject"],
        })

    return records


def _safe_int(val) -> int | None:
    try:
        return int(float(val)) if val not in (None, "", "nan") else None
    except (TypeError, ValueError):
        return None


def _safe_fetch_ward(ward_id: int | None) -> list[dict]:
    if ward_id is None:
        return []
    try:
        return fetch_area_polygons(scope="ward", ward_id=ward_id)
    except Exception:
        return []


# ── Leaflet JS ─────────────────────────────────────────────────────────────────

_AUDIT_JS = """
<script>
(function() {
  var PAYLOAD = JSON.parse(document.getElementById('ccmap-audit-payload').textContent);
  var STORE_KEY = 'ccmap_audit_cannot_determine_decisions';
  var decisions = {};
  try { decisions = JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch(e) {}

  var idx = 0;
  var overlays = [];
  var activeMode = 'base';  // base | buffer_union | concave_hull | edge_inject

  function saveDecisions() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(decisions)); } catch(e) {}
  }

  function getMap() {
    for (var k in window) {
      if (window[k] && window[k] instanceof L.Map) return window[k];
    }
    return null;
  }

  function clearOverlays() {
    var m = getMap();
    overlays.forEach(function(l) { if (m) m.removeLayer(l); });
    overlays = [];
  }

  function addRings(m, rings, color, label) {
    rings.forEach(function(ring) {
      var l = L.polygon(ring, {color: color, fillColor: color, fillOpacity: 0.15, weight: 2});
      l.bindPopup(label);
      l.addTo(m);
      overlays.push(l);
    });
  }

  function renderRecord(i) {
    var m = getMap(); if (!m || !PAYLOAD[i]) return;
    var rec = PAYLOAD[i];
    clearOverlays();

    addRings(m, rec.csv_rings, '#1565c0', 'CSV ward: ' + rec.csv_ward_id);
    addRings(m, rec.api_rings, '#e65100', 'API ward: ' + rec.api_ward_id);

    var geoRings = rec['geo_' + activeMode];
    if (geoRings) {
      addRings(m, geoRings, '#7b1fa2', 'Geometry: ' + activeMode);
    }

    if (rec.lat && rec.lng) {
      m.setView([rec.lat, rec.lng], 14);
      var marker = L.circleMarker([rec.lat, rec.lng], {
        radius: 7, color: '#fff', fillColor: '#d32f2f', fillOpacity: 1, weight: 2
      }).bindPopup('Order: ' + rec.order_code);
      marker.addTo(m);
      overlays.push(marker);
    }

    var counter = document.getElementById('ccmap-audit-counter');
    if (counter) counter.textContent = (i + 1) + ' / ' + PAYLOAD.length;
    var codeEl = document.getElementById('ccmap-audit-order');
    if (codeEl) codeEl.textContent = rec.order_code || '—';

    var d = decisions[rec.order_code] || null;
    ['csv', 'api', 'indeterminate'].forEach(function(v) {
      var btn = document.getElementById('ccmap-audit-btn-' + v);
      if (btn) btn.style.outline = d === v ? '3px solid #000' : '';
    });
  }

  function nextUndecided() {
    for (var j = 0; j < PAYLOAD.length; j++) {
      var ni = (idx + 1 + j) %% PAYLOAD.length;
      if (!decisions[PAYLOAD[ni].order_code]) { idx = ni; renderRecord(idx); return; }
    }
    idx = (idx + 1) %% PAYLOAD.length;
    renderRecord(idx);
  }

  window.addEventListener('load', function() {
    setTimeout(function() {
      function decide(val) {
        if (PAYLOAD[idx]) { decisions[PAYLOAD[idx].order_code] = val; saveDecisions(); renderRecord(idx); }
      }
      document.getElementById('ccmap-audit-btn-csv').addEventListener('click', function() { decide('csv'); });
      document.getElementById('ccmap-audit-btn-api').addEventListener('click', function() { decide('api'); });
      document.getElementById('ccmap-audit-btn-indeterminate').addEventListener('click', function() { decide('indeterminate'); });
      document.getElementById('ccmap-audit-btn-next').addEventListener('click', nextUndecided);
      document.getElementById('ccmap-audit-btn-prev').addEventListener('click', function() {
        idx = (idx - 1 + PAYLOAD.length) %% PAYLOAD.length;
        renderRecord(idx);
      });

      ['buffer_union', 'concave_hull', 'edge_inject', 'base'].forEach(function(mode) {
        var btn = document.getElementById('ccmap-geo-' + mode);
        if (!btn) return;
        btn.addEventListener('click', function() {
          activeMode = mode;
          document.querySelectorAll('.ccmap-geo-btn').forEach(function(b) { b.style.fontWeight = ''; });
          btn.style.fontWeight = 'bold';
          renderRecord(idx);
        });
      });

      document.getElementById('ccmap-audit-btn-export').addEventListener('click', function() {
        var blob = new Blob([JSON.stringify(decisions, null, 2)], {type: 'application/json'});
        var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
        a.download = 'audit_decisions.json'; a.click();
      });

      renderRecord(0);
    }, 800);
  });
})();
</script>
"""

_AUDIT_CONTROL_HTML = """
<div id="ccmap-audit-control" style="
  position:fixed; top:12px; right:12px; z-index:9999;
  background:#fff; border:2px solid #333; border-radius:8px;
  padding:14px 18px; min-width:300px; font-family:sans-serif; font-size:13px;
  box-shadow:0 4px 16px rgba(0,0,0,.25);">
  <div style="font-weight:700; font-size:14px; margin-bottom:8px;">
    Cannot-Determine Audit
  </div>
  <div style="margin-bottom:6px;">
    Order: <strong id="ccmap-audit-order">—</strong>
    &nbsp; <span id="ccmap-audit-counter" style="color:#666"></span>
  </div>
  <div style="display:flex; gap:6px; margin-bottom:10px;">
    <button id="ccmap-audit-btn-prev"
      style="flex:1;padding:5px;cursor:pointer;border:1px solid #999;border-radius:4px">&#9664; Prev</button>
    <button id="ccmap-audit-btn-next"
      style="flex:1;padding:5px;cursor:pointer;border:1px solid #999;border-radius:4px">Next &#9654;</button>
  </div>
  <div style="margin-bottom:8px; font-weight:600; font-size:12px;">Geometry preview:</div>
  <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:10px;">
    <button id="ccmap-geo-base" class="ccmap-geo-btn"
      style="padding:4px 8px;cursor:pointer;border:1px solid #999;border-radius:4px;font-size:11px">Base</button>
    <button id="ccmap-geo-buffer_union" class="ccmap-geo-btn"
      style="padding:4px 8px;cursor:pointer;border:1px solid #999;border-radius:4px;font-size:11px">Buffer Union</button>
    <button id="ccmap-geo-concave_hull" class="ccmap-geo-btn"
      style="padding:4px 8px;cursor:pointer;border:1px solid #999;border-radius:4px;font-size:11px">Concave Hull</button>
    <button id="ccmap-geo-edge_inject" class="ccmap-geo-btn"
      style="padding:4px 8px;cursor:pointer;border:1px solid #999;border-radius:4px;font-size:11px">Edge Inject</button>
  </div>
  <div style="margin-bottom:8px; font-weight:600; font-size:12px;">Determination:</div>
  <div style="display:flex; gap:6px; margin-bottom:8px;">
    <button id="ccmap-audit-btn-csv"
      style="flex:1;padding:6px;cursor:pointer;background:#1565c0;color:#fff;border:none;border-radius:4px;font-size:12px">
      CSV correct
    </button>
    <button id="ccmap-audit-btn-api"
      style="flex:1;padding:6px;cursor:pointer;background:#e65100;color:#fff;border:none;border-radius:4px;font-size:12px">
      API correct
    </button>
    <button id="ccmap-audit-btn-indeterminate"
      style="flex:1;padding:6px;cursor:pointer;background:#555;color:#fff;border:none;border-radius:4px;font-size:12px">
      Indeterm.
    </button>
  </div>
  <div style="text-align:right;">
    <button id="ccmap-audit-btn-export"
      style="font-size:11px;padding:4px 10px;cursor:pointer;border:1px solid #999;border-radius:4px">
      Export JSON
    </button>
  </div>
</div>
"""


# ── Entry point ────────────────────────────────────────────────────────────────

def build_audit_map(
    cannot_determine_rows: list[dict],
    *,
    buffer_m: float = 50.0,
    alpha: float = 0.3,
    max_neighbors: int = 3,
    partner_source: str | None = None,
    limit: int = 0,
) -> str:
    """
    Build the interactive cannot-determine audit HTML page.
    Returns the full HTML string.
    """
    if not cannot_determine_rows:
        return "<html><body><p>No cannot-determine rows provided.</p></body></html>"

    records = _build_audit_records(
        cannot_determine_rows,
        buffer_m=buffer_m,
        alpha=alpha,
        max_neighbors=max_neighbors,
        limit=limit,
    )

    if not records:
        return "<html><body><p>No records could be built from provided rows.</p></body></html>"

    first = records[0]
    center = [first.get("lat") or 10.76, first.get("lng") or 106.66]
    audit_map = folium.Map(location=center, zoom_start=13, prefer_canvas=True)

    payload_json = json.dumps(records, ensure_ascii=False)
    audit_map.get_root().html.add_child(Element(
        f'<script type="application/json" id="ccmap-audit-payload">'
        f'{payload_json}</script>'
    ))

    audit_map.get_root().html.add_child(Element(_AUDIT_CONTROL_HTML))
    audit_map.get_root().html.add_child(Element(_AUDIT_JS))

    return audit_map.get_root().render()
