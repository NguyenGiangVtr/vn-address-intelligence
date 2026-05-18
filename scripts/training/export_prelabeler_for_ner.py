#!/usr/bin/env python3
"""
Export prelabeler cases (passed) to Label Studio JSON format for NER training.

Usage:
    python scripts/training/export_prelabeler_for_ner.py --output data/prelabeler_export.json
    python scripts/training/export_prelabeler_for_ner.py --min-samples 100 --since 2026-05-01
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Bootstrap import paths
for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

import _bootstrap_import_paths  # noqa: E402
_bootstrap_import_paths.install()

from sqlalchemy import text
from app.core.database import SessionLocal


def query_passed_cases(
    only_passed: bool = True,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query ai.prelabeler_testcases for passed cases.
    
    Args:
        only_passed: If True, only return cases with test_result->>'passed' = true
        since: ISO timestamp string, only return cases updated after this time
    
    Returns:
        List of dicts with keys: id, input, expected, created_at, updated_at
    """
    sql_parts = [
        """
        SELECT id, input, expected, test_result, created_at, updated_at
        FROM ai.prelabeler_testcases
        WHERE expected IS NOT NULL
          AND jsonb_array_length(expected) > 0
        """
    ]
    
    params = {}
    
    if only_passed:
        sql_parts.append("AND (test_result->>'passed')::boolean = true")
    
    if since:
        sql_parts.append("AND updated_at > :since")
        params["since"] = since
    
    sql_parts.append("ORDER BY created_at DESC")
    
    sql = text("\n".join(sql_parts))
    
    session = SessionLocal()
    try:
        rows = session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]
    finally:
        session.close()


def find_text_offset(raw_address: str, text: str, used_ranges: List[tuple]) -> Optional[tuple]:
    """
    Find character offset of text in raw_address, avoiding already used ranges.
    
    Args:
        raw_address: The full address string
        text: The entity text to find
        used_ranges: List of (start, end) tuples already assigned
    
    Returns:
        (start, end) tuple if found, None otherwise
    """
    if not text:
        return None
    
    # Try to find all occurrences
    start_pos = 0
    while True:
        idx = raw_address.find(text, start_pos)
        if idx == -1:
            break
        
        end_idx = idx + len(text)
        
        # Check if this range overlaps with any used range
        overlaps = False
        for used_start, used_end in used_ranges:
            if not (end_idx <= used_start or idx >= used_end):
                overlaps = True
                break
        
        if not overlaps:
            return (idx, end_idx)
        
        start_pos = idx + 1
    
    return None


def prelabeler_case_to_labelstudio(
    case_id: str,
    raw_address: str,
    expected: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Convert a prelabeler case to Label Studio format.
    
    Args:
        case_id: Unique case identifier
        raw_address: The raw address string
        expected: List of {"label": "NUM", "text": "268"} entities
    
    Returns:
        Label Studio format dict
    """
    annotations = []
    used_ranges = []
    skipped = []
    
    for entity in expected:
        label = entity.get("label", "").upper()
        text = entity.get("text", "").strip()
        
        if not label or not text:
            continue
        
        # Find character offset
        offset = find_text_offset(raw_address, text, used_ranges)
        
        if offset is None:
            skipped.append({"label": label, "text": text})
            continue
        
        start, end = offset
        used_ranges.append((start, end))
        
        annotations.append({
            "type": "labels",
            "value": {
                "start": start,
                "end": end,
                "text": text,
                "labels": [label]
            }
        })
    
    result = {
        "id": case_id,
        "data": {"text": raw_address},
        "annotations": [{"result": annotations}] if annotations else []
    }
    
    if skipped:
        result["_skipped_entities"] = skipped
    
    return result


def merge_with_labelstudio(
    prelabeler_data: List[Dict[str, Any]],
    labelstudio_path: Path
) -> List[Dict[str, Any]]:
    """
    Merge prelabeler export with existing Label Studio export.
    
    Args:
        prelabeler_data: List of prelabeler cases in Label Studio format
        labelstudio_path: Path to Label Studio export JSON
    
    Returns:
        Merged list
    """
    if not labelstudio_path.exists():
        print(f"Warning: Label Studio file not found: {labelstudio_path}")
        return prelabeler_data
    
    try:
        with open(labelstudio_path, "r", encoding="utf-8") as f:
            ls_data = json.load(f)
        
        if not isinstance(ls_data, list):
            print(f"Warning: Label Studio file is not a list, skipping merge")
            return prelabeler_data
        
        # Merge: Label Studio first, then prelabeler
        merged = ls_data + prelabeler_data
        print(f"Merged {len(ls_data)} Label Studio samples with {len(prelabeler_data)} prelabeler cases")
        return merged
    
    except Exception as e:
        print(f"Warning: Failed to merge with Label Studio file: {e}")
        return prelabeler_data


def export_prelabeler_cases(
    output_path: Path,
    min_samples: int = 50,
    merge_labelstudio_path: Optional[Path] = None,
    since: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export prelabeler cases to Label Studio JSON format.
    
    Args:
        output_path: Output JSON file path
        min_samples: Minimum number of samples required
        merge_labelstudio_path: Optional path to Label Studio export to merge
        since: Optional ISO timestamp to filter cases
    
    Returns:
        Export statistics dict
    """
    print(f"Querying ai.prelabeler_testcases...")
    cases = query_passed_cases(only_passed=True, since=since)
    
    print(f"Found {len(cases)} passed cases")
    
    if len(cases) < min_samples:
        raise ValueError(
            f"Insufficient samples: {len(cases)} < {min_samples}. "
            f"Need at least {min_samples} passed cases to export."
        )
    
    print(f"Converting to Label Studio format...")
    labelstudio_data = []
    total_skipped = 0
    
    for case in cases:
        case_id = str(case["id"])
        raw_address = case["input"]
        expected = case["expected"] or []
        
        item = prelabeler_case_to_labelstudio(case_id, raw_address, expected)
        labelstudio_data.append(item)
        
        if "_skipped_entities" in item:
            total_skipped += len(item["_skipped_entities"])
    
    # Merge with Label Studio if requested
    if merge_labelstudio_path:
        labelstudio_data = merge_with_labelstudio(labelstudio_data, merge_labelstudio_path)
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labelstudio_data, f, ensure_ascii=False, indent=2)
    
    stats = {
        "total_cases": len(cases),
        "total_samples": len(labelstudio_data),
        "skipped_entities": total_skipped,
        "output_path": str(output_path),
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }
    
    print(f"\n{'='*60}")
    print(f"Export completed successfully!")
    print(f"{'='*60}")
    print(f"Total prelabeler cases: {stats['total_cases']}")
    print(f"Total samples (after merge): {stats['total_samples']}")
    print(f"Skipped entities (not found in text): {stats['skipped_entities']}")
    print(f"Output: {stats['output_path']}")
    print(f"{'='*60}\n")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Export prelabeler cases to Label Studio JSON for NER training"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: data/prelabeler_export_YYYYMMDD_HHMMSS.json)"
    )
    
    parser.add_argument(
        "--min-samples",
        type=int,
        default=50,
        help="Minimum number of passed cases required (default: 50)"
    )
    
    parser.add_argument(
        "--merge-labelstudio",
        type=str,
        default=None,
        help="Path to Label Studio export JSON to merge with prelabeler cases"
    )
    
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only export cases updated after this ISO timestamp (e.g., 2026-05-01T00:00:00)"
    )
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"data/prelabeler_export_{timestamp}.json")
    
    # Determine merge path
    merge_path = Path(args.merge_labelstudio) if args.merge_labelstudio else None
    
    try:
        stats = export_prelabeler_cases(
            output_path=output_path,
            min_samples=args.min_samples,
            merge_labelstudio_path=merge_path,
            since=args.since,
        )
        
        # Write stats to companion file
        stats_path = output_path.with_suffix(".stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"Export statistics saved to: {stats_path}")
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
