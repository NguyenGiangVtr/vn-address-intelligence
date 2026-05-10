"""Interactive multi-ward mismatch correction map builder.

Generates a self-contained HTML page with:
- CSV ward boundaries (blue) and API ward boundaries (orange) as Leaflet overlays
- "CSV correct / API correct" correction buttons per mismatch record
- "Next uncorrected" navigation
- Decisions saved to browser localStorage
"""
from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from typing import Any

import folium
from branca.element import Element
from sqlalchemy import text

from app.core.database import engine
from app.tools.boundary_visualization.folium_boundaries import (
    extract_polygon_rings,
    add_boundaries_to_map,
)
from app.tools.boundary_visualization.load_polygons import fetch_area_polygons

logger = logging.getLogger(__name__)

# ── CSV reader ─────────────────────────────────────────────────────────────────

def _read_all_mismatches(csv_path: str) -> list[dict]:
    """Read api_report_detailed CSV and return all_match=false rows."""
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            all_match = str(row.get("all_match", "true")).strip().lower()
            if all_match in ("false", "0", ""):
                rows.append(dict(row))
    return rows


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _fetch_admin_names(ward_ids: list[int], district_ids: list[int], province_ids: list[int]) -> dict:
    """Return {level_id_key: name} dict for given admin IDs."""
    names: dict[str, str] = {}
    if not any([ward_ids, district_ids, province_ids]):
        return names

    with engine.connect() as conn:
        if province_ids:
            q = conn.execute(
                text("SELECT province_id, province_name FROM mat.province WHERE province_id = ANY(:ids)"),
                {"ids": list(set(province_ids))},
            )
            for row in q:
                names[f"province_{row[0]}"] = row[1] or ""

        if district_ids:
            q = conn.execute(
                text("SELECT district_id, district_name FROM mat.district WHERE district_id = ANY(:ids)"),
                {"ids": list(set(district_ids))},
            )
            for row in q:
                names[f"district_{row[0]}"] = row[1] or ""

        if ward_ids:
            q = conn.execute(
                text("SELECT ward_id, ward_name FROM mat.ward WHERE ward_id = ANY(:ids)"),
                {"ids": list(set(ward_ids))},
            )
            for row in q:
                names[f"ward_{row[0]}"] = row[1] or ""

    return names


def _fetch_ward_polygons_for_ids(ward_ids: list[int]) -> dict[int, list]:
    """Return {ward_id: [ring, ...]} from the area_polygon table."""
    result: dict[int, list] = {}
    for wid in set(ward_ids):
        if wid is None:
            continue
        try:
            polys = fetch_area_polygons(scope="ward", ward_id=wid)
            rings: list = []
            for p in polys:
                rings.extend(extract_polygon_rings(p.get("coordinates")))
            if rings:
                result[wid] = rings
        except Exception as exc:
            logger.debug("Failed to fetch polygon for ward %s: %s", wid, exc)
    return result


# ── Record builder ─────────────────────────────────────────────────────────────

def _safe_int(val) -> int | None:
    try:
        return int(float(val)) if val not in (None, "", "nan") else None
    except (TypeError, ValueError):
        return None


def _build_records(mismatch_rows: list[dict], admin_names: dict, ward_polygons: dict) -> list[dict]:
    records: list[dict] = []
    for row in mismatch_rows:
        lat = row.get("lat")
        lng = row.get("lng")
        csv_w = _safe_int(row.get("csv_ward_id"))
        api_w = _safe_int(row.get("api_ward_id"))

        records.append({
            "order_code":      row.get("order_code", ""),
            "lat":             lat,
            "lng":             lng,
            "csv_province_id": _safe_int(row.get("csv_province_id")),
            "csv_district_id": _safe_int(row.get("csv_district_id")),
            "csv_ward_id":     csv_w,
            "api_province_id": _safe_int(row.get("api_province_id")),
            "api_district_id": _safe_int(row.get("api_district_id")),
            "api_ward_id":     api_w,
            "csv_ward_name":   admin_names.get(f"ward_{csv_w}", ""),
            "api_ward_name":   admin_names.get(f"ward_{api_w}", ""),
            "csv_rings":       ward_polygons.get(csv_w, []),
            "api_rings":       ward_polygons.get(api_w, []),
        })
    return records


# ── JS + HTML injection ────────────────────────────────────────────────────────

_LEAFLET_JS = """
<script>
(function() {
  var PAYLOAD = JSON.parse(document.getElementById('ccmap-mismatch-payload').textContent);
  var STORE_KEY = 'ccmap_mismatch_corrections';
  var corrections = {};
  try { corrections = JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch(e) {}

  var idx = 0;
  var csvLayers = [];
  var apiLayers = [];

  function saveCorrections() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(corrections)); } catch(e) {}
  }

  function getMap() {
    // Folium sets window.map_* — find the first L.Map instance
    for (var k in window) {
      if (window[k] && window[k] instanceof L.Map) return window[k];
    }
    return null;
  }

  function clearOverlays() {
    var m = getMap();
    if (!m) return;
    csvLayers.forEach(function(l) { m.removeLayer(l); });
    apiLayers.forEach(function(l) { m.removeLayer(l); });
    csvLayers = [];
    apiLayers = [];
  }

  function renderRecord(i) {
    var m = getMap();
    if (!m || !PAYLOAD[i]) return;
    var rec = PAYLOAD[i];
    clearOverlays();

    var csvColor = '%(csv_color)s';
    var apiColor = '%(api_color)s';

    rec.csv_rings.forEach(function(ring) {
      var l = L.polygon(ring, {color: csvColor, fillColor: csvColor, fillOpacity: 0.15, weight: 2});
      l.bindPopup('CSV ward: ' + rec.csv_ward_name);
      l.addTo(m);
      csvLayers.push(l);
    });
    rec.api_rings.forEach(function(ring) {
      var l = L.polygon(ring, {color: apiColor, fillColor: apiColor, fillOpacity: 0.15, weight: 2, dashArray: '6 4'});
      l.bindPopup('API ward: ' + rec.api_ward_name);
      l.addTo(m);
      apiLayers.push(l);
    });

    if (rec.lat && rec.lng) {
      m.setView([rec.lat, rec.lng], 14);
      L.circleMarker([rec.lat, rec.lng], {radius: 6, color: '#fff', fillColor: '#333', fillOpacity: 1}).addTo(m);
    }

    var counter = document.getElementById('ccmap-counter');
    if (counter) counter.textContent = (i + 1) + ' / ' + PAYLOAD.length;

    var codeEl = document.getElementById('ccmap-order-code');
    if (codeEl) codeEl.textContent = rec.order_code || '—';

    var csvLabel = document.getElementById('ccmap-csv-label');
    if (csvLabel) csvLabel.textContent = rec.csv_ward_name || ('Ward ID: ' + rec.csv_ward_id);
    var apiLabel = document.getElementById('ccmap-api-label');
    if (apiLabel) apiLabel.textContent = rec.api_ward_name || ('Ward ID: ' + rec.api_ward_id);

    var decision = corrections[rec.order_code] || null;
    document.getElementById('ccmap-btn-csv').style.fontWeight = decision === 'csv' ? 'bold' : '';
    document.getElementById('ccmap-btn-api').style.fontWeight = decision === 'api' ? 'bold' : '';
  }

  function nextUncorrected() {
    for (var j = 0; j < PAYLOAD.length; j++) {
      var ni = (idx + 1 + j) %% PAYLOAD.length;
      if (!corrections[PAYLOAD[ni].order_code]) { idx = ni; renderRecord(idx); return; }
    }
    idx = (idx + 1) %% PAYLOAD.length;
    renderRecord(idx);
  }

  window.addEventListener('load', function() {
    setTimeout(function() {
      document.getElementById('ccmap-btn-csv').addEventListener('click', function() {
        if (PAYLOAD[idx]) { corrections[PAYLOAD[idx].order_code] = 'csv'; saveCorrections(); renderRecord(idx); }
      });
      document.getElementById('ccmap-btn-api').addEventListener('click', function() {
        if (PAYLOAD[idx]) { corrections[PAYLOAD[idx].order_code] = 'api'; saveCorrections(); renderRecord(idx); }
      });
      document.getElementById('ccmap-btn-next').addEventListener('click', nextUncorrected);
      document.getElementById('ccmap-btn-prev').addEventListener('click', function() {
        idx = (idx - 1 + PAYLOAD.length) %% PAYLOAD.length;
        renderRecord(idx);
      });
      document.getElementById('ccmap-btn-export').addEventListener('click', function() {
        var blob = new Blob([JSON.stringify(corrections, null, 2)], {type: 'application/json'});
        var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
        a.download = 'mismatch_corrections.json'; a.click();
      });
      renderRecord(0);
    }, 800);
  });
})();
</script>
"""

_CONTROL_HTML = """
<div id="ccmap-control" style="
  position: fixed; top: 12px; right: 12px; z-index: 9999;
  background: #fff; border: 2px solid #333; border-radius: 8px;
  padding: 14px 18px; min-width: 280px; font-family: sans-serif; font-size: 13px;
  box-shadow: 0 4px 16px rgba(0,0,0,.25);">
  <div style="font-weight:700; font-size:14px; margin-bottom:8px;">
    Mismatch Correction Tool
  </div>
  <div style="margin-bottom:4px;">
    Order: <strong id="ccmap-order-code">—</strong>
    &nbsp; <span id="ccmap-counter" style="color:#666"></span>
  </div>
  <div style="display:flex; gap:6px; margin-bottom:8px;">
    <button id="ccmap-btn-prev"
      style="flex:1;padding:5px;cursor:pointer;border:1px solid #999;border-radius:4px">&#9664; Prev</button>
    <button id="ccmap-btn-next"
      style="flex:1;padding:5px;cursor:pointer;border:1px solid #999;border-radius:4px">Next uncorrected &#9654;</button>
  </div>
  <div style="margin-bottom:6px; font-size:12px; color:#555;">
    <span style="color:%(csv_color)s; font-weight:700;">&#9632;</span>
    CSV ward: <span id="ccmap-csv-label">—</span>
  </div>
  <div style="margin-bottom:10px; font-size:12px; color:#555;">
    <span style="color:%(api_color)s; font-weight:700;">&#9632;</span>
    API ward: <span id="ccmap-api-label">—</span>
  </div>
  <div style="display:flex; gap:6px;">
    <button id="ccmap-btn-csv"
      style="flex:1;padding:6px;cursor:pointer;background:%(csv_color)s;color:#fff;border:none;border-radius:4px">
      CSV correct
    </button>
    <button id="ccmap-btn-api"
      style="flex:1;padding:6px;cursor:pointer;background:%(api_color)s;color:#fff;border:none;border-radius:4px">
      API correct
    </button>
  </div>
  <div style="margin-top:8px; text-align:right;">
    <button id="ccmap-btn-export"
      style="font-size:11px;padding:4px 10px;cursor:pointer;border:1px solid #999;border-radius:4px">
      Export JSON
    </button>
  </div>
</div>
"""


# ── Entry point ────────────────────────────────────────────────────────────────

def build_mismatch_correction_map(
    detailed_csv_path: str,
    *,
    csv_color: str = "#1565c0",
    api_color: str = "#e65100",
) -> str:
    """
    Build the interactive mismatch correction HTML page.
    Returns the full HTML string.
    """
    mismatch_rows = _read_all_mismatches(detailed_csv_path)
    logger.info("Mismatch rows found: %d", len(mismatch_rows))

    if not mismatch_rows:
        return "<html><body><p>No mismatch rows found in the report.</p></body></html>"

    # Collect unique IDs for batch DB lookups
    ward_ids    = [_safe_int(r.get("csv_ward_id"))  for r in mismatch_rows] + \
                  [_safe_int(r.get("api_ward_id"))   for r in mismatch_rows]
    district_ids = [_safe_int(r.get("csv_district_id")) for r in mismatch_rows] + \
                   [_safe_int(r.get("api_district_id")) for r in mismatch_rows]
    province_ids = [_safe_int(r.get("csv_province_id")) for r in mismatch_rows] + \
                   [_safe_int(r.get("api_province_id")) for r in mismatch_rows]

    ward_ids_clean    = [i for i in ward_ids    if i is not None]
    district_ids_clean = [i for i in district_ids if i is not None]
    province_ids_clean = [i for i in province_ids if i is not None]

    admin_names   = _fetch_admin_names(ward_ids_clean, district_ids_clean, province_ids_clean)
    ward_polygons = _fetch_ward_polygons_for_ids(ward_ids_clean)

    records = _build_records(mismatch_rows, admin_names, ward_polygons)

    # Build base Folium map
    first = records[0]
    center = [first.get("lat") or 10.76, first.get("lng") or 106.66]
    boundary_map = folium.Map(location=center, zoom_start=13, prefer_canvas=True)

    # Embed payload as JSON script tag
    payload_json = json.dumps(records, ensure_ascii=False)
    payload_el = Element(
        f'<script type="application/json" id="ccmap-mismatch-payload">'
        f'{payload_json}</script>'
    )
    boundary_map.get_root().html.add_child(payload_el)

    # Control panel HTML
    ctrl_html = _CONTROL_HTML % {"csv_color": csv_color, "api_color": api_color}
    boundary_map.get_root().html.add_child(Element(ctrl_html))

    # Interactive JS — %% is literal % (Python format string)
    js_code = _LEAFLET_JS % {"csv_color": csv_color, "api_color": api_color}
    boundary_map.get_root().html.add_child(Element(js_code))

    return boundary_map.get_root().render()
