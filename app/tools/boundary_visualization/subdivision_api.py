"""Subdivision API client — batch coordinate → province/district/ward lookup.

Calls the local spatial subdivision functions directly (in-process) to avoid
3× HTTP round-trips per batch.  The HTTP helpers (prepare_request / send_request)
are also provided for external/standalone use.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import time
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

VNAI_API_PATH = "/api/spatial/subdivide"
_ORDERS_FIELDNAMES = ("order_code", "lat", "lng", "province_id", "district_id", "ward_id")


# ── Transport helpers (HTTP mode) ─────────────────────────────────────────────

def _build_client(verify: bool) -> httpx.Client:
    transport = httpx.HTTPTransport(retries=2)
    return httpx.Client(transport=transport, verify=verify, timeout=30)


def prepare_request(locations: list[dict]) -> dict:
    """Build {url, headers, body} for the local spatial subdivide endpoint."""
    base_url = os.getenv("VNAI_API_BASE_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("VNAI_API_TOKEN", "")
    return {
        "url": f"{base_url}{VNAI_API_PATH}",
        "headers": {"Authorization": f"Bearer {token}"} if token else {},
        "body": {
            "points": [
                {"lat": loc["Lat"], "lon": loc["Lng"], "order_id": loc.get("Partner")}
                for loc in locations
            ],
            "level": "ward",
        },
    }


def send_request(req: dict, *, verify: bool = False) -> dict:
    """POST req to req['url'] and return {ok, status, text}."""
    with _build_client(verify) as client:
        r = client.post(req["url"], json=req["body"], headers=req["headers"])
    return {"ok": r.is_success, "status": r.status_code, "text": r.text}


# ── In-process direct subdivide (preferred for the compare endpoint) ──────────

def _direct_subdivide(locations: list[dict]) -> list[dict]:
    """
    Call the spatial PostGIS functions directly (no HTTP).
    Returns list of {lat, lng, province_id, district_id, ward_id}.
    Falls back to empty dict values when PostGIS is unavailable.
    """
    try:
        from app.core.database import SessionLocal
        from app.api.spatial import _check_postgis, _point_in_polygon_query, _nearest_unit_query

        results: list[dict] = []
        db = SessionLocal()
        try:
            has_postgis = _check_postgis(db)

            def _query(lat: float, lon: float, level: str) -> dict | None:
                if has_postgis:
                    r = _point_in_polygon_query(db, lat, lon, level)
                    if r:
                        return r
                return _nearest_unit_query(db, lat, lon, level)

            for loc in locations:
                lat = float(loc["Lat"])
                lng = float(loc["Lng"])
                p = _query(lat, lng, "province")
                d = _query(lat, lng, "district")
                w = _query(lat, lng, "ward")
                results.append({
                    "lat": lat,
                    "lng": lng,
                    "province_id": p["unit_id"] if p else None,
                    "district_id": d["unit_id"] if d else None,
                    "ward_id":     w["unit_id"] if w else None,
                })
        finally:
            db.close()
        return results
    except Exception as exc:
        logger.warning("Direct subdivide failed: %s", exc)
        return []


# ── Response normalizer ───────────────────────────────────────────────────────

def _normalize_response_items(raw_text: str) -> list[dict]:
    """Parse raw API JSON text into a flat list of item dicts."""
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            return data
        for key in ("items", "results", "data", "Data", "Items", "results"):
            val = data.get(key)
            if isinstance(val, list):
                return val
    except Exception:
        pass
    return []


# ── CSV reader ────────────────────────────────────────────────────────────────

def read_orders_csv(csv_path: str) -> list[dict]:
    """Read orders CSV (lat, lng, province_id, district_id, ward_id, order_code)."""
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({
                "order_code":  row.get("order_code", ""),
                "lat":         _safe_float(row.get("lat")),
                "lng":         _safe_float(row.get("lng")),
                "province_id": _safe_int(row.get("province_id")),
                "district_id": _safe_int(row.get("district_id")),
                "ward_id":     _safe_int(row.get("ward_id")),
            })
    return rows


def _safe_float(val) -> float | None:
    try:
        return float(val) if val not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int | None:
    try:
        f = float(val)
        return int(f) if f == f else None
    except (TypeError, ValueError):
        return None


# ── Batch helpers ─────────────────────────────────────────────────────────────

def chunk_rows(rows: list[dict], batch_size: int) -> list[list[dict]]:
    return [rows[i: i + batch_size] for i in range(0, len(rows), batch_size)]


def build_locations(rows: list[dict]) -> list[dict]:
    return [{"Lat": r["lat"], "Lng": r["lng"], "Partner": None} for r in rows]


def timestamp_token() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _record_error(errors: list, chunk_idx: int, exc: Exception, rows: list[dict]) -> None:
    errors.append({
        "chunk":   chunk_idx,
        "error":   str(exc),
        "rows":    len(rows),
    })


# ── Main batch runner ─────────────────────────────────────────────────────────

def run_subdivision_batches(
    orders_rows: list[dict],
    *,
    batch_size: int = 500,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    verbose: bool = True,
) -> tuple[list[dict], list[dict]]:
    """
    Process orders_rows in batches.
    Returns (all_result_rows, errors).
    Uses direct in-process spatial calls for efficiency.
    """
    from app.tools.boundary_visualization.comparison_logic import align_items_to_rows

    chunks = chunk_rows(orders_rows, batch_size)
    all_rows: list[dict] = []
    errors: list[dict] = []

    for idx, chunk in enumerate(chunks):
        if verbose:
            logger.info("Processing chunk %d/%d (%d rows)", idx + 1, len(chunks), len(chunk))

        locations = build_locations(chunk)
        api_items: list[dict] = []
        last_exc: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                api_items = _direct_subdivide(locations)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                logger.warning("Chunk %d attempt %d failed: %s", idx + 1, attempt, exc)
                if attempt < max_retries:
                    time.sleep(retry_delay)

        if last_exc is not None:
            _record_error(errors, idx, last_exc, chunk)
            from app.tools.boundary_visualization.comparison_logic import append_no_match_row
            for row in chunk:
                append_no_match_row(all_rows, row)
            continue

        batch_result_rows = align_items_to_rows(api_items, chunk)
        all_rows.extend(batch_result_rows)

        if verbose:
            matched = sum(1 for r in batch_result_rows if r.get("api_matched"))
            logger.info("  Chunk %d: %d/%d matched", idx + 1, matched, len(chunk))

    return all_rows, errors
