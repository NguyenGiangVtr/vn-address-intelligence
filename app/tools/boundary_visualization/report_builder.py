"""Report builder: convert comparison row dicts → DataFrame + summary."""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


def build_report_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Convert result row dicts to a DataFrame with bool match columns."""
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    for col in ("province_match", "district_match", "ward_match", "all_match", "api_matched"):
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)
    return df


def summarize_report(df: pd.DataFrame) -> dict:
    """Return a match-rate summary dict."""
    total = len(df)
    if total == 0:
        return {
            "total_rows": 0,
            "api_matched_rows": 0,
            "province_match_pct": 0.0,
            "district_match_pct": 0.0,
            "ward_match_pct": 0.0,
            "all_match_pct": 0.0,
        }

    matched = int(df["api_matched"].sum()) if "api_matched" in df.columns else total

    def _pct(col: str) -> float:
        if col not in df.columns or matched == 0:
            return 0.0
        return round(float(df[col].sum()) / matched * 100, 2)

    return {
        "total_rows":        total,
        "api_matched_rows":  matched,
        "province_match_pct": _pct("province_match"),
        "district_match_pct": _pct("district_match"),
        "ward_match_pct":     _pct("ward_match"),
        "all_match_pct":      _pct("all_match"),
    }


def print_summary(summary: dict) -> None:
    print(f"Total rows      : {summary['total_rows']}")
    print(f"API matched     : {summary['api_matched_rows']}")
    print(f"Province match  : {summary['province_match_pct']:.1f}%")
    print(f"District match  : {summary['district_match_pct']:.1f}%")
    print(f"Ward match      : {summary['ward_match_pct']:.1f}%")
    print(f"All match       : {summary['all_match_pct']:.1f}%")


def write_outputs(
    df: pd.DataFrame,
    output_dir: str = "data",
    timestamp: str = "",
) -> dict:
    """Write detailed CSV to output_dir. Returns {'detail': path}."""
    os.makedirs(output_dir, exist_ok=True)
    ts = timestamp or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    detail_path = os.path.join(output_dir, f"api_report_detailed__{ts}.csv")
    df.to_csv(detail_path, index=False, encoding="utf-8-sig")
    return {"detail": detail_path}
