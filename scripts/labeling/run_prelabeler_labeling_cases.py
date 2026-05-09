#!/usr/bin/env python3
"""
Run PreLabeler labeling-case suite from JSON (same semantics as UI):
- For each case, run PreLabeler.predict()
- Validate expected entities must be present
- If strict=true, also fail on unexpected entities

Co the dat min-pass-rate (default 1.0 = 100%) qua --min-pass-rate.
Khi chay tren GitHub Actions, neu env $GITHUB_STEP_SUMMARY ton tai,
ket qua se duoc append vao day duoi dang Markdown table de hien thi
truc tiep tren tab "Summary" cua workflow run.
"""

from __future__ import annotations

import argparse
import json
import os
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


def _write_github_step_summary(
    total: int,
    passed: int,
    pass_rate: float,
    threshold: float,
    failures: list[dict],
) -> None:
    """Ghi summary markdown vao $GITHUB_STEP_SUMMARY neu co."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    status = "✅ PASSED" if pass_rate >= threshold else "❌ FAILED"
    lines = [
        f"## PreLabeler regression — {status}",
        "",
        f"- **Pass rate**: `{passed}/{total}` ({pass_rate:.1%})",
        f"- **Threshold**: `{threshold:.1%}`",
        f"- **Total cases**: `{total}`",
        "",
    ]
    if failures:
        lines.append("### Failed cases")
        lines.append("")
        lines.append("| Case ID | Missing | Unexpected | Validation errors |")
        lines.append("|---|---|---|---|")
        for f in failures[:50]:  # cap to keep summary readable
            missing = ", ".join(f"`{lab}:{txt}`" for lab, txt in f["missing"]) or "—"
            unexpected = ", ".join(f"`{lab}:{txt}`" for lab, txt in f["unexpected"]) or "—"
            errors = ", ".join(f"`{e}`" for e in f["validation_errors"]) or "—"
            lines.append(f"| `{f['id']}` | {missing} | {unexpected} | {errors} |")
        if len(failures) > 50:
            lines.append("")
            lines.append(f"_… and {len(failures) - 50} more not shown._")

    try:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError as exc:
        print(f"warn: cannot write GITHUB_STEP_SUMMARY: {exc}", file=sys.stderr)


def run_suite(test_file: Path, min_pass_rate: float) -> int:
    payload = json.loads(test_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input file must be a JSON array.")

    total = len(payload)
    passed = 0
    failures: list[dict] = []

    for case in payload:
        case_id = str(case.get("id") or f"case_{passed + 1}")
        inp = case.get("input", {}) or {}
        expected = case.get("expected", []) or []

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

        failures.append({
            "id": case_id,
            "missing": missing,
            "unexpected": unexpected,
            "validation_errors": validation_errors,
            "actual": actual_pairs,
        })

        print(f"[FAIL] {case_id}")
        if missing:
            print(f"  missing   : {missing}")
        if unexpected:
            print(f"  unexpected: {unexpected}")
        if validation_errors:
            print(f"  invalid   : {validation_errors}")
        print(f"  actual    : {actual_pairs}")

    pass_rate = (passed / total) if total > 0 else 1.0
    print(f"\nResult: {passed}/{total} passed ({pass_rate:.1%})")
    print(f"Min pass-rate threshold: {min_pass_rate:.1%}")

    _write_github_step_summary(
        total=total,
        passed=passed,
        pass_rate=pass_rate,
        threshold=min_pass_rate,
        failures=failures,
    )

    return 0 if pass_rate >= min_pass_rate else 1


def _parse_min_pass_rate(value: str) -> float:
    """Chap nhan dang `0.95` (decimal trong [0,1]) hoac `95%` (co dau %).

    Khong tu dong dien giai `95` (khong dau %) la `0.95` — yeu cau ro rang.
    """
    s = str(value or "").strip()
    if not s:
        raise argparse.ArgumentTypeError("min-pass-rate khong duoc rong")

    is_percent = s.endswith("%")
    body = s[:-1].strip() if is_percent else s
    try:
        v = float(body)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"min-pass-rate khong phai so: {value!r}") from exc

    if is_percent:
        v = v / 100.0
    if not 0.0 <= v <= 1.0:
        raise argparse.ArgumentTypeError(
            f"min-pass-rate phai trong [0,1] (decimal) hoac [0%,100%]: {value!r}"
        )
    return v


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        default="scripts/labeling/prelabeler_labeling_cases.json",
        help="Path to labeling-case JSON file",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=_parse_min_pass_rate,
        default=1.0,
        help="Min pass-rate de coi la pass (vd: 0.95 hoac 95%%). Mac dinh 1.0 (100%%).",
    )
    args = parser.parse_args()
    return run_suite(Path(args.file), args.min_pass_rate)


if __name__ == "__main__":
    raise SystemExit(main())
