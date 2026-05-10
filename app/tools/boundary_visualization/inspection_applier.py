"""Apply report inspection verdicts to a detailed CSV.

For rows with determination='likely_api_correct', copies api_* columns onto
csv_* columns, then recomputes match statistics.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from app.tools.boundary_visualization.report_builder import build_report_dataframe, summarize_report

logger = logging.getLogger(__name__)


# ── Private helpers ────────────────────────────────────────────────────────────

def _load_likely_api_correct_codes(inspection_path: str) -> set[str]:
    """Return set of order_codes that have determination='likely_api_correct'."""
    with open(inspection_path, encoding="utf-8-sig") as fh:
        data = json.load(fh)

    rows = data.get("rows") or data if isinstance(data, list) else []
    return {
        str(r.get("order_code", ""))
        for r in rows
        if r.get("determination") == "likely_api_correct"
    }


def _source_report_from_inspection(inspection_path: str) -> str | None:
    """Read the source_report path stored in the inspection JSON."""
    try:
        with open(inspection_path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
        return data.get("source_report")
    except Exception:
        return None


def _recompute_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute province/district/ward/all match flags from csv_*/api_* id columns."""
    for level in ("province", "district", "ward"):
        csv_col = f"csv_{level}_id"
        api_col = f"api_{level}_id"
        match_col = f"{level}_match"
        if csv_col in df.columns and api_col in df.columns:
            df[match_col] = (
                df[csv_col].notna() & df[api_col].notna() &
                (df[csv_col].astype(str) == df[api_col].astype(str))
            )

    bool_cols = [c for c in ("province_match", "district_match", "ward_match") if c in df.columns]
    if bool_cols:
        df["all_match"] = df[bool_cols].all(axis=1)

    return df


# ── Entry point ────────────────────────────────────────────────────────────────

def apply_inspection(
    inspection_json_path: str,
    detailed_csv_path: str,
) -> tuple[pd.DataFrame, dict]:
    """
    For rows with determination='likely_api_correct', copy api_* → csv_*,
    then recompute match stats.

    Returns (adjusted_dataframe, summary_payload).
    summary_payload contains {before: summary_dict, after: summary_dict}.
    """
    # Load data
    df = pd.read_csv(detailed_csv_path, dtype=str, encoding="utf-8-sig")
    rows_before = build_report_dataframe(df.to_dict("records"))
    summary_before = summarize_report(rows_before)

    # Determine which orders to adjust
    api_correct_codes = _load_likely_api_correct_codes(inspection_json_path)
    logger.info("Applying api_correct to %d order codes", len(api_correct_codes))

    # Copy api_* → csv_* for those rows
    mask = df["order_code"].astype(str).isin(api_correct_codes)
    for level in ("province", "district", "ward"):
        api_col = f"api_{level}_id"
        csv_col = f"csv_{level}_id"
        if api_col in df.columns and csv_col in df.columns:
            df.loc[mask, csv_col] = df.loc[mask, api_col]

    df = _recompute_matches(df)
    rows_after = build_report_dataframe(df.to_dict("records"))
    summary_after = summarize_report(rows_after)

    summary_payload = {
        "adjusted_count": int(mask.sum()),
        "before": summary_before,
        "after":  summary_after,
    }

    return df, summary_payload
