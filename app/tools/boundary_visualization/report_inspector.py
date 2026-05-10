"""Report inspection: label each all_match=false row with a determination verdict.

Verdicts:
  likely_csv_correct        — spatial query confirms the lat/lng is inside the CSV ward boundary
  likely_api_correct        — spatial query confirms the lat/lng is inside the API ward boundary
  ambiguous_both_evidence   — point is inside both ward boundaries (or both lack boundary data)
  indeterminate             — cannot determine from available spatial data
"""
from __future__ import annotations

import csv
import logging
from typing import Any

from sqlalchemy import text

from app.core.database import engine

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_int(val) -> int | None:
    try:
        return int(float(val)) if val not in (None, "", "nan") else None
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        return float(val) if val not in (None, "", "nan") else None
    except (TypeError, ValueError):
        return None


def _point_in_ward(lat: float, lng: float, ward_id: int) -> bool | None:
    """
    Return True if the point (lat, lng) falls inside any polygon for ward_id.
    Returns None when no polygon data is available (uses ST_Contains via PostGIS).
    """
    try:
        sql = text("""
            SELECT COUNT(*) FROM mat.area_polygon
            WHERE ward_id = :wid
              AND COALESCE(is_deleted, false) = false
              AND ST_Contains(
                  ST_SetSRID(ST_GeomFromGeoJSON(coordinates::text), 4326),
                  ST_SetSRID(ST_Point(:lng, :lat), 4326)
              )
        """)
        with engine.connect() as conn:
            count = conn.execute(sql, {"wid": ward_id, "lat": lat, "lng": lng}).scalar()
        return (count or 0) > 0
    except Exception as exc:
        logger.debug("_point_in_ward failed for ward %s: %s", ward_id, exc)
        return None


def _determine(
    lat: float,
    lng: float,
    csv_ward_id: int | None,
    api_ward_id: int | None,
) -> str:
    """Apply spatial evidence to assign a determination verdict."""
    in_csv = _point_in_ward(lat, lng, csv_ward_id) if csv_ward_id else None
    in_api = _point_in_ward(lat, lng, api_ward_id) if api_ward_id else None

    if in_csv is True and in_api is not True:
        return "likely_csv_correct"
    if in_api is True and in_csv is not True:
        return "likely_api_correct"
    if in_csv is True and in_api is True:
        return "ambiguous_both_evidence"
    # Both None or both False
    return "indeterminate"


# ── CSV reader ─────────────────────────────────────────────────────────────────

def _read_detailed_csv(csv_path: str) -> list[dict]:
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rows.append(dict(row))
    return rows


# ── Entry point ────────────────────────────────────────────────────────────────

def run_report_inspection(
    detailed_csv_path: str,
    *,
    limit: int = 0,
) -> dict:
    """
    Read api_report_detailed CSV, evaluate each all_match=false row,
    and label each with a determination verdict.

    Returns {"summary": {...}, "rows": [...], "source_report": path}.
    """
    all_rows = _read_detailed_csv(detailed_csv_path)
    mismatch_rows = [
        r for r in all_rows
        if str(r.get("all_match", "true")).strip().lower() in ("false", "0", "")
    ]

    if limit > 0:
        mismatch_rows = mismatch_rows[:limit]

    verdict_counts: dict[str, int] = {
        "likely_csv_correct":      0,
        "likely_api_correct":      0,
        "ambiguous_both_evidence": 0,
        "indeterminate":           0,
    }

    result_rows: list[dict] = []
    for row in mismatch_rows:
        lat = _safe_float(row.get("lat"))
        lng = _safe_float(row.get("lng"))
        csv_ward = _safe_int(row.get("csv_ward_id"))
        api_ward = _safe_int(row.get("api_ward_id"))

        if lat is None or lng is None:
            determination = "indeterminate"
        else:
            determination = _determine(lat, lng, csv_ward, api_ward)

        verdict_counts[determination] = verdict_counts.get(determination, 0) + 1

        result_rows.append({**row, "determination": determination})

    return {
        "source_report": detailed_csv_path,
        "total_mismatch": len(mismatch_rows),
        "summary":        verdict_counts,
        "rows":           result_rows,
    }
