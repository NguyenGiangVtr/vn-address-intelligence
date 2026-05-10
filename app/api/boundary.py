from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

import folium

from app.tools.boundary_visualization.folium_boundaries import add_boundaries_to_map, extract_polygon_rings
from app.tools.boundary_visualization.load_polygons import fetch_area_polygons

router = APIRouter()
logger = logging.getLogger("VNAI_BoundaryAPI")

_DATA_DIR = Path("data")
_PAGES_DIR = Path("ui/pages")


def _ensure_dirs() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _PAGES_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


# ── GET /map ──────────────────────────────────────────────────────────────────

@router.get("/map", tags=["Bản đồ địa giới"], summary="Tạo bản đồ ranh giới hành chính")
def generate_boundary_map(
    scope: str = Query("province", pattern="^(province|district|ward)$"),
    province_id: Optional[int] = None,
    district_id: Optional[int] = None,
    ward_id: Optional[int] = None,
    zoom_start: int = 11,
):
    try:
        polygons = fetch_area_polygons(scope=scope, province_id=province_id, district_id=district_id, ward_id=ward_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.warning("Boundary polygon fetch failed, fallback to empty map: %s", exc)
        polygons = []

    def _map_center(polygons):
        lats, lngs = [], []
        for polygon in polygons:
            rings = extract_polygon_rings(polygon.get("coordinates"))
            for ring in rings:
                for lat, lng in ring:
                    lats.append(lat)
                    lngs.append(lng)
        return [sum(lats) / len(lats), sum(lngs) / len(lngs)] if lats else [10.762622, 106.660172]

    center = _map_center(polygons)
    boundary_map = folium.Map(location=center, zoom_start=zoom_start, prefer_canvas=True)
    ring_count = add_boundaries_to_map(boundary_map, polygons)
    folium.LayerControl(collapsed=False).add_to(boundary_map)

    _ensure_dirs()
    filename = f"boundary_map_{scope}_{_timestamp()}.html"
    output_path = _PAGES_DIR / filename
    boundary_map.save(str(output_path))

    return {"url": f"/pages/{filename}", "rings": ring_count}


# ── POST /compare ─────────────────────────────────────────────────────────────

@router.post("/compare", tags=["Bản đồ địa giới"], summary="So sánh đơn hàng với API phân giải địa chỉ")
async def compare_orders(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV với cột lat,lng,province_id,district_id,ward_id,order_code"),
    batch_size: int = Query(500, ge=10, le=5000),
):
    from app.tools.boundary_visualization.subdivision_api import run_subdivision_batches, read_orders_csv, timestamp_token
    from app.tools.boundary_visualization.report_builder import build_report_dataframe, summarize_report, write_outputs

    _ensure_dirs()
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        orders_rows = read_orders_csv(tmp_path)
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(status_code=400, detail=f"CSV parse error: {exc}")

    if len(orders_rows) > 5000:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=400,
            detail="Batch > 5000 rows not yet supported in synchronous mode. Split your file."
        )

    try:
        all_rows, errors = run_subdivision_batches(
            orders_rows,
            batch_size=batch_size,
            verbose=True,
        )
    except Exception as exc:
        logger.exception("run_subdivision_batches failed")
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Subdivision error: {exc}")

    os.unlink(tmp_path)

    df = build_report_dataframe(all_rows)
    summary = summarize_report(df)
    ts = timestamp_token()
    write_outputs(df, output_dir=str(_DATA_DIR), timestamp=ts)

    detail_rows = df.head(2000).to_dict("records")

    return {
        "summary":     summary,
        "detail_rows": detail_rows,
        "errors":      errors,
        "report_file": f"api_report_detailed__{ts}.csv",
    }


# ── GET /reports ─────────────────────────────────────────────────────────────

@router.get("/reports", tags=["Bản đồ địa giới"], summary="Danh sách báo cáo chi tiết đã tạo")
def list_reports():
    _ensure_dirs()
    files = sorted(_DATA_DIR.glob("api_report_detailed__*.csv"), reverse=True)
    return {"files": [f.name for f in files]}


# ── GET /mismatch ─────────────────────────────────────────────────────────────

@router.get("/mismatch", tags=["Bản đồ địa giới"], summary="Bản đồ sửa lỗi đa-ward mismatch")
def generate_mismatch_map(
    detailed_csv: Optional[str] = Query(None, description="Path to api_report_detailed*.csv; defaults to latest in data/"),
    csv_color: str = Query("#1565c0"),
    api_color: str = Query("#e65100"),
):
    from app.tools.boundary_visualization.mismatch_correction_builder import build_mismatch_correction_map

    csv_path = _resolve_report_csv(detailed_csv)
    if not csv_path:
        raise HTTPException(status_code=404, detail="No api_report_detailed CSV found in data/")

    try:
        html = build_mismatch_correction_map(csv_path, csv_color=csv_color, api_color=api_color)
    except Exception as exc:
        logger.exception("build_mismatch_correction_map failed")
        raise HTTPException(status_code=500, detail=str(exc))

    _ensure_dirs()
    ts = _timestamp()
    filename = f"mismatch_correction_{ts}.html"
    output_path = _PAGES_DIR / filename
    output_path.write_text(html, encoding="utf-8")

    return {"url": f"/pages/{filename}"}


# ── GET /audit ────────────────────────────────────────────────────────────────

@router.get("/audit", tags=["Bản đồ địa giới"], summary="Tạo bản đồ audit cannot-determine")
def generate_audit_map(
    source_json: Optional[str] = Query(None, description="Path to report_inspection JSON or api_report_detailed CSV"),
    buffer_m: float = 50.0,
    alpha: float = 0.3,
    limit: int = 0,
):
    from app.tools.boundary_visualization.audit_builder import build_audit_map

    rows = _load_audit_rows(source_json)
    if not rows:
        raise HTTPException(status_code=404, detail="No cannot-determine rows found")

    try:
        html = build_audit_map(rows, buffer_m=buffer_m, alpha=alpha, limit=limit)
    except Exception as exc:
        logger.exception("build_audit_map failed")
        raise HTTPException(status_code=500, detail=str(exc))

    _ensure_dirs()
    ts = _timestamp()
    filename = f"audit_map_{ts}.html"
    output_path = _PAGES_DIR / filename
    output_path.write_text(html, encoding="utf-8")

    return {"url": f"/pages/{filename}", "record_count": len(rows)}


# ── POST /inspect ─────────────────────────────────────────────────────────────

@router.post("/inspect", tags=["Bản đồ địa giới"], summary="Phân tích báo cáo mismatch")
def run_inspection(
    detailed_csv: Optional[str] = Query(None),
    limit: int = 0,
):
    from app.tools.boundary_visualization.report_inspector import run_report_inspection

    csv_path = _resolve_report_csv(detailed_csv)
    if not csv_path:
        raise HTTPException(status_code=404, detail="No api_report_detailed CSV found in data/")

    try:
        result = run_report_inspection(csv_path, limit=limit)
    except Exception as exc:
        logger.exception("run_report_inspection failed")
        raise HTTPException(status_code=500, detail=str(exc))

    # Save JSON output
    _ensure_dirs()
    ts = _timestamp()
    out_dir = _DATA_DIR / "report_inspection"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"report_inspection_{ts}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "summary":      result["summary"],
        "total_mismatch": result["total_mismatch"],
        "rows":         result["rows"][:500],   # cap preview at 500
        "inspection_file": str(out_path),
    }


# ── POST /inspect/apply ───────────────────────────────────────────────────────

@router.post("/inspect/apply", tags=["Bản đồ địa giới"], summary="Áp dụng kết quả inspection vào báo cáo")
def apply_inspection_to_report(
    inspection_json: str = Query(..., description="Path to report_inspection_*.json"),
    detailed_csv: Optional[str] = Query(None),
):
    from app.tools.boundary_visualization.inspection_applier import apply_inspection, _source_report_from_inspection

    csv_path = detailed_csv
    if not csv_path:
        csv_path = _source_report_from_inspection(inspection_json) or _resolve_report_csv(None)
    if not csv_path or not Path(csv_path).exists():
        raise HTTPException(status_code=404, detail="Detailed CSV not found")

    if not Path(inspection_json).exists():
        raise HTTPException(status_code=404, detail=f"Inspection JSON not found: {inspection_json}")

    try:
        df, summary_payload = apply_inspection(inspection_json, csv_path)
    except Exception as exc:
        logger.exception("apply_inspection failed")
        raise HTTPException(status_code=500, detail=str(exc))

    _ensure_dirs()
    ts = _timestamp()
    out_path = _DATA_DIR / f"api_report_adjusted__{ts}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    return {
        "summary_before":  summary_payload["before"],
        "summary_after":   summary_payload["after"],
        "adjusted_count":  summary_payload["adjusted_count"],
        "download_url":    f"/api/boundary/download?file={out_path.name}",
    }


# ── GET /download ─────────────────────────────────────────────────────────────

@router.get("/download", tags=["Bản đồ địa giới"], summary="Tải file CSV từ data/")
def download_report(file: str = Query(...)):
    file_path = _DATA_DIR / Path(file).name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path), media_type="text/csv", filename=file_path.name)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_report_csv(explicit_path: Optional[str]) -> Optional[str]:
    """Return path to the detailed CSV: explicit_path if given, else latest in data/."""
    if explicit_path:
        p = Path(explicit_path)
        return str(p) if p.exists() else None
    files = sorted(_DATA_DIR.glob("api_report_detailed__*.csv"), reverse=True)
    return str(files[0]) if files else None


def _load_audit_rows(source_path: Optional[str]) -> list[dict]:
    """
    Load cannot-determine rows from a JSON inspection file or CSV report.
    Defaults to the latest api_report_detailed CSV in data/.
    """
    import csv as csv_module

    if source_path and source_path.endswith(".json") and Path(source_path).exists():
        with open(source_path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
        rows = data.get("rows") or []
        return [r for r in rows if r.get("determination") in ("indeterminate", "ambiguous_both_evidence")]

    # Fall back to CSV
    csv_path = _resolve_report_csv(source_path)
    if not csv_path:
        return []
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv_module.DictReader(fh):
            all_match = str(row.get("all_match", "true")).strip().lower()
            if all_match in ("false", "0", ""):
                rows.append(dict(row))
    return rows
