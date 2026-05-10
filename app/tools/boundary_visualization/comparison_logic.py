"""Comparison logic for batch order vs spatial API subdivision results.

All functions are pure Python (stdlib + dicts/lists only) — no DB or I/O.
"""
from __future__ import annotations


# ── Helpers ───────────────────────────────────────────────────────────────────

def _int_or_none(val):
    if val is None or val == "":
        return None
    try:
        f = float(val)
        return None if f != f else int(f)   # NaN check
    except (TypeError, ValueError):
        return None


def _coord_key(lat, lng) -> str:
    """Canonical lat/lng key rounded to 4 decimal places."""
    try:
        return f"{round(float(lat), 4)},{round(float(lng), 4)}"
    except (TypeError, ValueError):
        return f"{lat},{lng}"


def extract_matched_list(api_response) -> list[dict]:
    """Extract flat item list from raw API response (list or dict wrapper)."""
    if not api_response:
        return []
    if isinstance(api_response, list):
        return api_response
    for key in ("items", "results", "data", "Data", "Items"):
        val = api_response.get(key)
        if isinstance(val, list):
            return val
    return []


def match_item(items: list[dict], lat, lng) -> dict | None:
    """Return the first item whose lat/lng matches (within 4-decimal rounding)."""
    target = _coord_key(lat, lng)
    for item in items:
        item_lat = item.get("lat", item.get("Lat", 0))
        item_lng = item.get("lng", item.get("Lng", 0))
        if _coord_key(item_lat, item_lng) == target:
            return item
    return None


def pick_best_item(items: list[dict]) -> dict | None:
    """Pick the best item: prefer items with a non-null ward_id."""
    if not items:
        return None
    for item in items:
        if item.get("ward_id") is not None:
            return item
    return items[0]


def partner_match_rows(items: list[dict], partner: str | None = None) -> list[dict]:
    """Filter items by partner name (pass-through when partner is None)."""
    if not partner:
        return items
    return [i for i in items if i.get("partner") == partner]


# ── Core comparison ───────────────────────────────────────────────────────────

def build_result_row(csv_row: dict, api_item: dict | None) -> dict:
    """
    Assemble a comparison row dict.
    csv_row must have: lat, lng, province_id, district_id, ward_id, order_code.
    When api_item is None all api_* are null and all match flags are False.
    """
    csv_p = _int_or_none(csv_row.get("province_id"))
    csv_d = _int_or_none(csv_row.get("district_id"))
    csv_w = _int_or_none(csv_row.get("ward_id"))

    if api_item:
        api_p = _int_or_none(api_item.get("province_id"))
        api_d = _int_or_none(api_item.get("district_id"))
        api_w = _int_or_none(api_item.get("ward_id"))
        province_match = api_p is not None and csv_p == api_p
        district_match = api_d is not None and csv_d == api_d
        ward_match     = api_w is not None and csv_w == api_w
        all_match      = province_match and district_match and ward_match
        api_matched    = True
    else:
        api_p = api_d = api_w = None
        province_match = district_match = ward_match = all_match = False
        api_matched = False

    return {
        "order_code":      csv_row.get("order_code"),
        "lat":             csv_row.get("lat"),
        "lng":             csv_row.get("lng"),
        "csv_province_id": csv_p,
        "csv_district_id": csv_d,
        "csv_ward_id":     csv_w,
        "api_province_id": api_p,
        "api_district_id": api_d,
        "api_ward_id":     api_w,
        "province_match":  province_match,
        "district_match":  district_match,
        "ward_match":      ward_match,
        "all_match":       all_match,
        "api_matched":     api_matched,
    }


def append_no_match_row(rows_list: list[dict], csv_row: dict) -> None:
    """Append a null/no-match row for a csv_row that got no API response."""
    rows_list.append(build_result_row(csv_row, None))


def align_items_to_rows(batch_items: list[dict], rows: list[dict]) -> list[dict]:
    """
    Match each input csv row to its API item by lat/lng coordinate key,
    build a result row for each, and return the full aligned list.
    """
    result_rows = []
    for row in rows:
        item = match_item(batch_items, row.get("lat", 0), row.get("lng", 0))
        result_rows.append(build_result_row(row, item))
    return result_rows
