# Boundary UI Integration Plan
**Source:** `ccmap_boundary_visualization`  
**Target:** `vn-address-intelligence`  
**Date:** 2026-05-10 (revised)  
**Status:** Draft v2

---

## Assumptions

1. The goal is to bring the *full UI workflow* from `ccmap_boundary_visualization` into `vn-address-intelligence` — not just the basic map view, which is already done.
2. The target project owns its own PostgreSQL/SQLAlchemy stack; psycopg2 + mypyutils from the source are replaced with the existing `engine` pattern already present in `app/core/database.py`.
3. The ccmap subdivision API client (`subdivision_api.py`) is specific to `localhost:44385` (the CCMap .NET service). In vn-address-intelligence, the comparison target will be its own `/api/v1/...` parse endpoint. The **comparison algorithm** (`comparison_logic.py`) is fully reusable; only the transport layer is adapted.
4. GitNexus re-analyze timed out in the sandbox — run it manually before any code edit: `cd ccmap_boundary_visualization && npx gitnexus analyze`. The MCP tools (`gitnexus_impact`, `gitnexus_context`) must also be connected to the IDE session before editing any symbol.
5. `app/geometry/` in vn-address-intelligence is a **completely different** PostGIS/SQLAlchemy implementation. Do NOT touch it. The shapely+pyproj geometry modules from the source are needed only by the cannot-determine audit tool and must be placed under `app/tools/boundary_visualization/geometry/` as an isolated sub-package.

---

## Current State: What Is Already Integrated

| File in vn-address-intelligence | Status | Notes |
|---|---|---|
| `app/tools/boundary_visualization/folium_boundaries.py` | ✅ Ported | Missing `fixed_color` param — Phase 0 fix required |
| `app/tools/boundary_visualization/load_polygons.py` | ✅ Ported | Migrated from psycopg2 to SQLAlchemy |
| `app/api/boundary.py` | ✅ Working | `GET /api/boundary/map` endpoint |
| `ui/pages/boundary-visualization.html` | ✅ Working | Basic map preview page |
| `ui/app.js` | ✅ Wired | Sidebar nav + fetch handler for boundary page |
| `app/geometry/buffer_union.py` | ✅ Production | PostGIS-based — do not touch |
| `app/geometry/concave_hull.py` | ✅ Production | PostGIS-based — do not touch |
| `app/geometry/edge_inject.py` | ✅ Production | PostGIS-based — do not touch |
| `app/services/spatial_mismatch.py` | ✅ Production | Separate pipeline — do not touch |

---

## Gap Analysis: What Is Missing

| Source file | Target destination | Priority |
|---|---|---|
| `folium_boundaries.py` — `fixed_color` param | Patch existing file | P0 |
| `comparison_logic.py` | `app/tools/boundary_visualization/comparison_logic.py` | P1 |
| `report_builder.py` | `app/tools/boundary_visualization/report_builder.py` | P1 |
| `subdivision_api.py` (adapted — see §1.3) | `app/tools/boundary_visualization/subdivision_api.py` | P1 |
| `visualize_first_mismatch.py` (refactored) | `app/tools/boundary_visualization/mismatch_correction_builder.py` | P2a |
| `geometry/crs.py` | `app/tools/boundary_visualization/geometry/crs.py` | P2b |
| `geometry/buffer_union.py` (shapely) | `app/tools/boundary_visualization/geometry/buffer_union.py` | P2b |
| `geometry/concave_hull.py` (shapely) | `app/tools/boundary_visualization/geometry/concave_hull.py` | P2b |
| `geometry/edge_inject.py` (shapely) | `app/tools/boundary_visualization/geometry/edge_inject.py` | P2b |
| `audit_bounds_cannot_determine.py` (refactored) | `app/tools/boundary_visualization/audit_builder.py` | P2b |
| `validate_mismatch_corrections.py` (report_inspection mode only) | `app/tools/boundary_visualization/report_inspector.py` | P3 |
| `apply_report_inspection_to_detailed.py` (refactored) | `app/tools/boundary_visualization/inspection_applier.py` | P3 |
| FastAPI: `/compare` endpoint | `app/api/boundary.py` | P1 |
| FastAPI: `/mismatch` endpoint | `app/api/boundary.py` | P2a |
| FastAPI: `/audit` endpoint | `app/api/boundary.py` | P2b |
| FastAPI: `/inspect` endpoint | `app/api/boundary.py` | P3 |
| UI: comparison section | `ui/pages/boundary-visualization.html` | P1 |
| UI: multi-ward mismatch section | `ui/pages/boundary-visualization.html` | P2a |
| UI: cannot-determine audit section | `ui/pages/boundary-visualization.html` | P2b |
| UI: inspection section | `ui/pages/boundary-visualization.html` | P3 |

---

## Implementation Plan

### Phase 0 — Fix Existing Gap (0.5 day)

**Problem:** `add_boundaries_to_map()` in the ported `folium_boundaries.py` is missing the `fixed_color` optional parameter. The cannot-determine audit tool (Phase 2b) uses this to render single-colour ward overlays. Without it, Phase 2b build will fail on import.

**Verify first:**
```bash
grep -n "fixed_color" app/tools/boundary_visualization/folium_boundaries.py
# Must return nothing — confirms the gap
```

**Change:** Add `fixed_color=None` and `fill_opacity=0.12` keyword-only parameters to `add_boundaries_to_map()`. Add the `if fixed_color is not None` rendering branch from the source (`ccmap_boundary_visualization/folium_boundaries.py`, lines ~80–100).

**Impact:** Only caller today is `app/api/boundary.py` — it passes no `fixed_color`, so it takes the default `None` path, identical to current behaviour. No change needed in the caller.

**Success criterion:** `add_boundaries_to_map(map_obj, polygons, fixed_color="#ff0000")` renders all rings in red without partner layer grouping. `add_boundaries_to_map(map_obj, polygons)` continues to work identically to before.

---

### Phase 1 — Comparison Workflow (3.5–4.5 days)

Brings the batch order-vs-API comparison capability into the project. This is the most operationally useful feature in the source project.

#### 1.1 Port `comparison_logic.py` (0.5 day)

**Copy as-is** to `app/tools/boundary_visualization/comparison_logic.py`. Zero external dependencies beyond the Python standard library. No changes required.

Key exports:
- `partner_match_rows()` — best per-partner match from an API response
- `build_result_row()` — assembles the full comparison row dict
- `align_items_to_rows()` — aligns API batch results to input rows by lat/lng coordinate key
- `append_no_match_row()` — fills a null row when API returns nothing
- `extract_matched_list()`, `match_item()`, `pick_best_item()` — helpers

**Success criterion:** `from app.tools.boundary_visualization.comparison_logic import build_result_row` imports with no errors.

#### 1.2 Port `report_builder.py` (0.5 day)

**Copy as-is** to `app/tools/boundary_visualization/report_builder.py`. Depends only on `pandas` and `os`.

Key exports: `build_report_dataframe()`, `summarize_report()`, `print_summary()`, `write_outputs()`.

**Success criterion:** Pass a hand-crafted list of row dicts → get back a DataFrame with `all_match`, `province_match`, `district_match`, `ward_match` bool columns.

#### 1.3 Adapt `subdivision_api.py` (1 day)

The source calls the CCMap .NET endpoint via a curl-template mechanism that depends on `mypyutils` (`parse_curl`, `send_curl_like_request`, `update_curl_dict`). These three are the **only** things that need replacing. The batch-run scaffolding (`chunk_rows`, `run_subdivision_batches`, retry logic, progress printing, alignment) is kept unchanged.

Create `app/tools/boundary_visualization/subdivision_api.py`:

**Keep unchanged:**
- `chunk_rows(rows, batch_size)`
- `build_locations(rows)` → `[{"Lat": ..., "Lng": ..., "Partner": None}]`
- `read_orders_csv(csv_path)` (same column schema as source)
- `_normalize_response_items(raw_text)`
- `_record_error(errors, ...)` 
- `run_subdivision_batches(orders_rows, *, ...)` — full retry+progress loop
- `timestamp_token()`

**Replace `mypyutils` transport with httpx:**
```python
import httpx
from app.core.config import settings   # provides VNAI_API_BASE_URL, VNAI_API_TOKEN

def _build_client(verify: bool) -> httpx.Client:
    transport = httpx.HTTPTransport(retries=2)
    return httpx.Client(transport=transport, verify=verify, timeout=30)

def prepare_request(locations: list) -> dict:
    """Returns {url, headers, json_body} — replaces mypyutils.parse_curl + update_curl_dict."""
    return {
        "url": f"{settings.VNAI_API_BASE_URL.rstrip('/')}{VNAI_API_PATH}",
        "headers": {"Authorization": f"Bearer {settings.VNAI_API_TOKEN}"},
        "body": {"Locations": locations},
    }

def send_request(req: dict, *, verify: bool) -> dict:
    """Returns {ok, status, text} — replaces mypyutils.send_curl_like_request."""
    with _build_client(verify) as client:
        r = client.post(req["url"], json=req["body"], headers=req["headers"])
    return {"ok": r.is_success, "status": r.status_code, "text": r.text}
```

Update `run_subdivision_batches` to call `prepare_request()` and `send_request()` instead of the curl helpers. The retry loop, error handling, and alignment logic are otherwise identical.

**Remove:** `build_raw_curl_subdivisions()`, `AUTH_BEARER_TOKEN`, `RAW_CURL_SUBDIVISIONS`, `ORDERS_FIELDNAMES` (field names move into `read_orders_csv` as a local constant), all `mypyutils` imports.

**Success criterion:** `run_subdivision_batches(rows)` hits the local vn-address-intelligence API and returns `(all_api_rows, errors)` in the same shape as the source.

#### 1.4 Add `POST /api/boundary/compare` endpoint (1 day)

Add to `app/api/boundary.py`:

```python
@router.post("/compare", tags=["Bản đồ địa giới"], summary="So sánh đơn hàng với API phân giải địa chỉ")
async def compare_orders(
    file: UploadFile = File(..., description="CSV với cột lat,lng,province_id,district_id,ward_id,order_code"),
    batch_size: int = Query(500, ge=10, le=5000),
):
```

- Saves upload to a temp file, calls `read_orders_csv()` → `run_subdivision_batches()` → `build_report_dataframe()` → `summarize_report()`.
- Returns `{ summary, detail_rows (up to 2000), errors }`.
- Also writes the full `api_report_detailed_*.csv` to `data/` for use by later phases.
- For batches > 5 000 rows: return a `202 Accepted` with a job token (background task via FastAPI `BackgroundTasks`) — implementation details TBD with team.

**Success criterion:** `curl -F "file=@orders.csv" http://localhost:8000/api/boundary/compare` returns JSON with province/district/ward match rates and at least one detail row.

#### 1.5 Add UI section: Comparison (1 day)

Add a collapsible section to `ui/pages/boundary-visualization.html` (after the existing map section):

- File upload input for `orders.csv`
- Batch size selector (default 500)
- Run button → `POST /api/boundary/compare` with `multipart/form-data`
- Summary stat cards (province / district / ward match %)
- Scrollable detail table (order_code, csv vs api ward, match flag)
- Download full CSV button

Follow the existing `fetch()` + status-dot + timing pattern already used for the map section in `ui/app.js`.

**Success criterion:** Upload the `orders.csv` from the source project, click Run, see match summary and be able to download the detailed report.

---

### Phase 2a — Multi-Ward Mismatch Correction Tool (2.5–3 days)

> **Correction from v1 plan:** `visualize_first_mismatch.py` was mischaracterized as a "quick single-mismatch visualizer." It is in fact a full-featured interactive correction tool for **multi-ward mismatches** — cases where the subdivision API returned ambiguous results spanning multiple ward IDs. It generates a Folium map with embedded Leaflet JS, localStorage-backed corrections, CSV vs API boundary overlays, layer toggles, and record navigation. It is a distinct tool from the cannot-determine audit (Phase 2b) and does **not** use shapely geometry — only polygon ring rendering from the DB.

#### 2a.1 Refactor into `mismatch_correction_builder.py` (1.5 days)

Create `app/tools/boundary_visualization/mismatch_correction_builder.py`.

**Keep (adapt DB calls from psycopg2 → SQLAlchemy):**
- `_row_is_multi_ward_mismatch(row)` — filters for rows where `all_match=false` AND the matched JSON contains ≥2 distinct ward IDs
- `_read_all_multi_ward_mismatches(csv_path)` — reads the detailed report CSV and returns filtered rows
- `_fetch_scope_polygons(conn, scope, ids)` — wraps `fetch_area_polygons()`; migrate to SQLAlchemy engine
- `_fetch_admin_names(conn, ids)` — queries `mat.province/district/ward`; migrate `RealDictCursor` → `engine.connect()` with `text()`
- `_serialize_polygons_for_js(polygons)` — extracts ring lists for embedding in JS payload
- `_build_records(conn, mismatch_rows)` — assembles per-order record dicts (lat/lng, csv/api admin names, geo rings)
- `_inject_interactive_ui(boundary_map, records, ...)` — embeds the ~300-line Leaflet JS + HTML controls panel into the Folium map

**New entry-point function (replaces `main()`):**
```python
def build_mismatch_correction_map(
    detailed_csv_path: str,
    *,
    csv_color: str = "#1565c0",
    api_color: str = "#e65100",
) -> str:
    """Returns the HTML string of the interactive correction map."""
```

**Remove:** `argparse`, `webbrowser`, `subprocess`, `socket`, `_open_map_via_http`, `_latest_detailed_report_csv` (the endpoint locates the file), `_load_env` (config comes from `app/core/config.py`), all `psycopg2` imports.

**Success criterion:** `build_mismatch_correction_map(csv_path)` returns an HTML string containing `ccmap-mismatch-payload` JSON, `ccmap-btn-csv`, `ccmap-btn-api` elements and `localStorage` calls. When opened in a browser it shows CSV (blue) and API (orange) ward boundaries with "CSV correct / API correct" buttons and "Next uncorrected" navigation.

#### 2a.2 Add `GET /api/boundary/mismatch` endpoint (0.5 day)

```python
@router.get("/mismatch", tags=["Bản đồ địa giới"], summary="Bản đồ sửa lỗi đa-ward mismatch")
def generate_mismatch_map(
    detailed_csv: Optional[str] = Query(None, description="Path to api_report_detailed*.csv; defaults to latest in data/"),
):
```

- Finds the latest `api_report_detailed*.csv` in `data/` if no path given.
- Calls `build_mismatch_correction_map()`.
- Saves HTML to `ui/pages/mismatch_correction_{timestamp}.html`.
- Returns `{ "url": "/pages/mismatch_correction_....html", "record_count": N }`.

**Success criterion:** `GET /api/boundary/mismatch` returns a URL; opening the HTML in a browser shows multi-ward correction UI with at least one record pre-loaded.

#### 2a.3 Add UI section: Multi-ward mismatch (0.5 day)

Add section to `ui/pages/boundary-visualization.html`:
- Select box listing available `api_report_detailed*.csv` files (populated by `GET /api/boundary/reports`)
- Generate button → calls `/api/boundary/mismatch`
- Iframe to preview the result (same pattern as the basic map section)
- Note: corrections are saved to browser `localStorage`, not sent to the server

---

### Phase 2b — Cannot-Determine Audit Tool (4–5 days)

This is the most complex feature. `audit_bounds_cannot_determine.py` generates a self-contained interactive HTML for orders the report inspector labelled `indeterminate` or `ambiguous_both_evidence`. It renders CSV vs API ward polygons, geometry method previews (buffer union, concave hull, edge inject), and records decisions in localStorage.

#### 2b.1 Port shapely+pyproj geometry helpers (0.5 day)

The audit tool uses metric-projection geometry (`EPSG:32648`) that is distinct from the PostGIS-based `app/geometry/`. Place the shapely versions in their own sub-package:

Create `app/tools/boundary_visualization/geometry/`:
- `crs.py` — copy as-is: `to_metric(geom, metric_epsg)`, `to_wgs84(geom, metric_epsg)` using `pyproj.Transformer`
- `buffer_union.py` — copy as-is: `expand_buffer_union(base_polygon, outlier_points, buffer_m, ...)`
- `concave_hull.py` — copy as-is: `redraw_concave_hull(...)`
- `edge_inject.py` — copy as-is: `inject_outlier_vertices(...)`
- `__init__.py` — re-export `expand_buffer_union`, `redraw_concave_hull`, `inject_outlier_vertices`

**Check `requirements.txt` before starting:**
```bash
python -c "import shapely, pyproj, pandas, httpx, branca; print('all ok')"
```
Add any missing packages. `branca` is needed for `branca.element.Element` used in all three audit tools.

**Success criterion:** `from app.tools.boundary_visualization.geometry import expand_buffer_union` imports cleanly. Calling it on a known shapely Polygon returns a new shapely geometry.

#### 2b.2 Refactor `audit_bounds_cannot_determine.py` → `audit_builder.py` (2.5 days)

This is the highest-risk step. The source is ~600+ lines with interleaved DB calls, geometry computation, and Folium/JS generation.

Create `app/tools/boundary_visualization/audit_builder.py`.

**New entry-point function (replaces `main()`):**
```python
def build_audit_map(
    cannot_determine_rows: list[dict],
    *,
    buffer_m: float = 50.0,
    alpha: float = 0.3,
    max_neighbors: int = 3,
    partner_source: Optional[str] = None,
    limit: int = 0,
) -> str:
    """Returns the HTML string of the interactive cannot-determine audit map."""
```

**Migration steps:**
1. Replace `get_connection()` + `RealDictCursor` with `from app.core.database import engine` and `with engine.connect() as conn: conn.execute(text(...))`
2. Replace `from geometry import ...` with `from app.tools.boundary_visualization.geometry import ...`
3. Replace `from folium_boundaries import extract_polygon_rings, add_boundaries_to_map` with the `app.tools.boundary_visualization` equivalents
4. Replace `from load_polygons import fetch_area_polygons` similarly
5. Remove all `argparse`, `webbrowser`, `subprocess`, `socket`, `_open_map_via_http`, `_load_env` scaffolding
6. Collapse `main()` into `build_audit_map()` — the `rows` parameter replaces reading from JSON file (the endpoint does that)

**Success criterion:** `build_audit_map(rows)` returns an HTML string that contains the `ccmap_audit_cannot_determine_decisions` localStorage key reference and Leaflet geometry previews. When opened in a browser, ward boundaries with geometry method toggle buttons are visible.

#### 2b.3 Add `GET /api/boundary/audit` endpoint (0.5 day)

```python
@router.get("/audit", tags=["Bản đồ địa giới"], summary="Tạo bản đồ audit cannot-determine")
def generate_audit_map(
    source_json: Optional[str] = Query(None, description="Path to report_inspection_cannot_determine.json"),
    buffer_m: float = 50.0,
    alpha: float = 0.3,
    limit: int = 0,
):
```

- Defaults to `correction_validation_output/report_inspection/report_inspection_cannot_determine.json` if no path given.
- Calls `build_audit_map(rows, ...)`.
- Saves HTML to `ui/pages/audit_map_{timestamp}.html`.
- Returns `{ "url": "/pages/audit_map_....html", "record_count": N }`.

#### 2b.4 Add UI section: Cannot-determine audit (0.5 day)

Add section to `ui/pages/boundary-visualization.html`:
- Select box for `cannot_determine.json` file
- Buffer (m), Alpha, Limit controls
- Generate button → `/api/boundary/audit`
- Iframe preview (same pattern as map section)

---

### Phase 3 — Report Inspection & Correction Application (2.5–3 days)

#### 3.1 Port `validate_mismatch_corrections.py` — report_inspection mode only (1 day)

The source has two modes (`corrections` and `report_inspection`). Only `report_inspection` is needed for the UI integration. Extract it into `app/tools/boundary_visualization/report_inspector.py`.

**New entry-point function:**
```python
def run_report_inspection(
    detailed_csv_path: str,
    *,
    limit: int = 0,
) -> dict:
    """
    Reads api_report_detailed*.csv, evaluates each all_match=false row, 
    and labels each as:
      likely_csv_correct | likely_api_correct | ambiguous_both_evidence | indeterminate
    Returns {"summary": {...}, "rows": [...], "source_report": path}
    """
```

- Replace `get_connection()` / psycopg2 with SQLAlchemy `engine`.
- The `corrections` mode logic is dropped entirely.

**Success criterion:** `run_report_inspection("data/api_report_detailed__20260504_101440.csv")` returns a dict with `rows` where each row has a `determination` field taking one of the four verdict values.

#### 3.2 Port `apply_report_inspection_to_detailed.py` → `inspection_applier.py` (0.5 day)

Create `app/tools/boundary_visualization/inspection_applier.py`.

**New entry-point function (wraps the core of `apply_report_inspection_to_detailed.main()`):**
```python
def apply_inspection(
    inspection_json_path: str,
    detailed_csv_path: str,
) -> tuple[pd.DataFrame, dict]:
    """
    For rows with determination='likely_api_correct', copies api_* columns onto csv_* columns,
    then recomputes match stats.
    Returns (adjusted_dataframe, summary_payload).
    """
```

Key internal functions to preserve as private helpers:
- `_load_likely_api_correct_codes(inspection_path)` → `set[str]`
- `_source_report_from_inspection(inspection_path)` → `str | None`

**Remove:** `argparse`, `main()`, all file-write logic (the endpoint handles output).

#### 3.3 Add `POST /api/boundary/inspect` endpoint (0.5 day)

```python
@router.post("/inspect", tags=["Bản đồ địa giới"], summary="Phân tích báo cáo mismatch")
def run_inspection(
    detailed_csv: Optional[str] = Query(None),
    limit: int = 0,
):
```

Returns: `{ summary, rows }` — verdict per mismatch row.

Also expose `POST /api/boundary/inspect/apply`:
```python
@router.post("/inspect/apply")
def apply_inspection_to_report(
    inspection_json: str = Query(...),
    detailed_csv: Optional[str] = Query(None),
):
```

Returns: `{ summary_before, summary_after, download_url }` — downloads the post-inspection detailed CSV.

#### 3.4 Add UI section: Inspection (0.5 day)

Add section to `ui/pages/boundary-visualization.html`:
- Select `api_report_detailed*.csv` to inspect
- Run Inspect button → `POST /api/boundary/inspect`
- Verdict summary counts (likely_csv_correct / likely_api_correct / ambiguous / indeterminate)
- Per-row results table with verdict and evidence
- Apply button → `POST /api/boundary/inspect/apply` → download adjusted CSV

---

## File Checklist (complete)

```
app/tools/boundary_visualization/
  __init__.py                         UPDATE — export new modules
  folium_boundaries.py                PATCH  — add fixed_color param   (Phase 0)
  load_polygons.py                    ✅ done
  comparison_logic.py                 CREATE — copy as-is              (Phase 1.1)
  report_builder.py                   CREATE — copy as-is              (Phase 1.2)
  subdivision_api.py                  CREATE — adapt transport layer   (Phase 1.3)
  mismatch_correction_builder.py      CREATE — refactor from source    (Phase 2a.1)
  audit_builder.py                    CREATE — refactor from source    (Phase 2b.2)
  report_inspector.py                 CREATE — extract from source     (Phase 3.1)
  inspection_applier.py               CREATE — adapt from source       (Phase 3.2)
  geometry/
    __init__.py                       CREATE                            (Phase 2b.1)
    crs.py                            CREATE — copy as-is              (Phase 2b.1)
    buffer_union.py                   CREATE — copy shapely version    (Phase 2b.1)
    concave_hull.py                   CREATE — copy shapely version    (Phase 2b.1)
    edge_inject.py                    CREATE — copy shapely version    (Phase 2b.1)

app/api/boundary.py
  POST /compare                       ADD                              (Phase 1.4)
  GET  /mismatch                      ADD                              (Phase 2a.2)
  GET  /audit                         ADD                              (Phase 2b.3)
  POST /inspect                       ADD                              (Phase 3.3)
  POST /inspect/apply                 ADD                              (Phase 3.3)

ui/pages/boundary-visualization.html  PATCH — 4 new collapsible sections
ui/app.js                             PATCH — JS handlers for new sections
```

---

## Dependency Check

Run before Phase 2b.1:
```bash
python -c "import shapely, pyproj, pandas, httpx, branca; print('all ok')"
```

| Package | Used by | Status |
|---|---|---|
| `folium` | existing map endpoint | ✅ present |
| `branca` | all three interactive builders | verify — in source requirements.txt |
| `shapely` | audit geometry sub-package | verify |
| `pyproj` | `crs.py` (EPSG:32648 projection) | verify |
| `pandas` | `report_builder`, `inspection_applier` | verify |
| `httpx` | adapted `subdivision_api` | verify |

---

## GitNexus Notes

**Index status:** The last successful index is from 2026-05-05 (736 nodes, 1112 edges, 35 execution flows). The `npx gitnexus analyze` background run timed out in the Linux sandbox — you must run it manually from the source project directory on your machine before making any code edits.

**Per CLAUDE.md rules:** Before editing any symbol in the source, run `gitnexus_impact` first. Key symbols and their blast radii based on code reading:

| Symbol | Direct callers | Risk |
|---|---|---|
| `add_boundaries_to_map` | `cli.py`, `audit_bounds_cannot_determine.py` | MEDIUM — Phase 0 patch must not break the audit tool |
| `extract_polygon_rings` | `cli.py`, `visualize_first_mismatch.py`, `audit_bounds_cannot_determine.py`, `validate_mismatch_corrections.py`, `app/api/boundary.py` | HIGH — used across all tools |
| `fetch_area_polygons` | `cli.py`, `visualize_first_mismatch.py`, `audit_bounds_cannot_determine.py`, `validate_mismatch_corrections.py` | HIGH — DB access layer, any signature change breaks 4 callers |
| `build_result_row` | `run_subdivision_compare.py` only | LOW |
| `build_report_dataframe` | `run_subdivision_compare.py`, `apply_report_inspection_to_detailed.py` | MEDIUM |

**Note:** `visualize_first_mismatch.py` does **NOT** call `add_boundaries_to_map` — it renders via embedded Leaflet JS (not Folium polygons). The v1 plan incorrectly listed it as a caller.

---

## Sequencing & Effort Estimate

| Phase | Work | Estimate |
|---|---|---|
| 0 | Patch `fixed_color` in `folium_boundaries.py` | 0.5 day |
| 1.1–1.2 | Copy `comparison_logic` + `report_builder` (near zero changes) | 0.5 day |
| 1.3 | Adapt `subdivision_api` — replace mypyutils transport with httpx | 1 day |
| 1.4 | Add `/compare` FastAPI endpoint | 1 day |
| 1.5 | Comparison UI section | 1 day |
| 2a.1 | Refactor `visualize_first_mismatch.py` → `mismatch_correction_builder.py` | 1.5 days |
| 2a.2–2a.3 | `/mismatch` endpoint + UI section | 1 day |
| 2b.1 | Port shapely geometry helpers | 0.5 day |
| 2b.2 | Refactor `audit_bounds_cannot_determine.py` → `audit_builder.py` | 2.5 days |
| 2b.3–2b.4 | `/audit` endpoint + UI section | 1 day |
| 3.1–3.2 | Port inspector + applier | 1.5 days |
| 3.3–3.4 | Inspection endpoints + UI section | 1 day |
| **Total** | | **~13 days** |

**Recommended order:** 0 → 1.1–1.2 → 1.3 → 1.4–1.5 → 2a → 2b.1 → 2b.2 → 2b.3–2b.4 → 3.

The highest-risk steps are 2b.2 (the audit builder refactor, due to the volume of interleaved Leaflet JS) and 1.3 (transport layer replacement). All others are relatively mechanical.
