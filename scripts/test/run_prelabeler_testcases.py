#!/usr/bin/env python3
"""
Run PreLabeler labeling-case suite from JSON (same semantics as UI):
- For each case, run PreLabeler.predict()
- Validate expected entities must be present
- If strict=true, also fail on unexpected entities
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.export_for_annotation import PreLabeler
from app.services.prelabeler_labeling_service import (
    first_expected_text,
    predictions_to_expected,
    validate_expected_against_actual,
)


def _norm(s: str) -> str:
    return str(s or "").strip().lower()


def run_suite(test_file: Path) -> int:
    payload = json.loads(test_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input file must be a JSON array.")

    total = len(payload)
    passed = 0
    for case in payload:
        case_id = str(case.get("id") or f"case_{passed + 1}")
        inp = case.get("input", {}) or {}
        expected = case.get("expected", []) or []
        strict = bool(case.get("strict", False))

        if isinstance(inp, dict):
            raw_address = str(inp.get("raw_address") or "")
            ward_name = inp.get("ward_name")
            district_name = inp.get("district_name")
            province_name = inp.get("province_name")
        else:
            raw_address = str(inp or "")
            ward_name = None
            district_name = None
            province_name = None

        # Dong bo voi API /prelabeler-cases/run:
        # Nếu không có admin trong input thì suy ra từ expected để đảm bảo cùng hành vi.
        ward_name = ward_name or first_expected_text(expected, "WDS")
        district_name = district_name or first_expected_text(expected, "DST")
        province_name = province_name or first_expected_text(expected, "PRO")

        predictions = PreLabeler.predict(
            raw_address=raw_address,
            ward_name=ward_name,
            district_name=district_name,
            province_name=province_name,
            known_streets=set(),
        )
        actual = predictions_to_expected(predictions)
        actual_pairs = [(a["label"], _norm(a["text"])) for a in actual]

        validation = validate_expected_against_actual(
            raw_address=raw_address,
            expected=expected,
            actual=actual,
        )
        missing = [
            (str(d.get("expected", {}).get("label") or ""), _norm(str(d.get("expected", {}).get("text") or "")))
            for d in validation.get("details", [])
            if not d.get("found")
        ]
        unexpected = [
            (str(u.get("label") or ""), _norm(str(u.get("text") or "")))
            for u in validation.get("unexpected", [])
        ]
        validation_errors = validation.get("validation_errors", [])
        ok = bool(validation.get("passed"))
        if ok:
            passed += 1
            print(f"[PASS] {case_id}")
            continue

        print(f"[FAIL] {case_id}")
        if missing:
            print(f"  missing   : {missing}")
        if unexpected:
            print(f"  unexpected: {unexpected}")
        if validation_errors:
            print(f"  invalid   : {validation_errors}")
        print(f"  actual    : {actual_pairs}")

    print(f"\nResult: {passed}/{total} passed")
    return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        default="scripts/labeling/prelabeler_labeling_cases.json",
        help="Path to labeling-case JSON file",
    )
    args = parser.parse_args()
    return run_suite(Path(args.file))


if __name__ == "__main__":
    raise SystemExit(main())
