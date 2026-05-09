#!/usr/bin/env python3
"""
Refresh PreLabeler labeling cases theo logic hien tai va dong bo vao DB.

Tac vu:
1) Doc scripts/labeling/prelabeler_labeling_cases.json
2) Chay PreLabeler.predict cho tung case de cap nhat expected theo chuan moi
3) Ghi lai file JSON (in-place)
4) (Tuy chon) upsert vao ai.prelabeler_testcases

DRY: Toan bo logic build expected + admin Type+Name enforcement DUNG CHUNG voi
API /prelabeler-cases/random-predict thong qua app.services.prelabeler_labeling_service.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.db_connector import DBConnector
from app.ai.export_for_annotation import PreLabeler
from app.ai.utils.config_loader import load_config_with_env
from app.services.prelabeler_labeling_service import (
    enforce_admin_type_name,
    first_expected_text,
    predictions_to_expected,
)


def _predict_expected(case: dict) -> list[dict]:
    raw_input = case.get("input")
    old_expected = case.get("expected") or []

    if isinstance(raw_input, dict):
        raw_address = str(raw_input.get("raw_address") or "").strip()
        ward_name = str(raw_input.get("ward_name") or "").strip() or None
        district_name = str(raw_input.get("district_name") or "").strip() or None
        province_name = str(raw_input.get("province_name") or "").strip() or None
    else:
        raw_address = str(raw_input or "").strip()
        ward_name = None
        district_name = None
        province_name = None

    # Fallback: lay admin tu expected cu neu input khong khai bao.
    if not ward_name:
        ward_name = first_expected_text(old_expected, "WDS")
    if not district_name:
        district_name = first_expected_text(old_expected, "DST")
    if not province_name:
        province_name = first_expected_text(old_expected, "PRO")

    predictions = PreLabeler.predict(
        raw_address=raw_address,
        ward_name=ward_name,
        district_name=district_name,
        province_name=province_name,
        known_streets=set(),
    )

    expected = predictions_to_expected(predictions)
    expected = enforce_admin_type_name(
        expected=expected,
        raw_address=raw_address,
        ward_name=ward_name,
        district_name=district_name,
        province_name=province_name,
    )

    # Sap theo (label, text) de output JSON on dinh.
    expected.sort(key=lambda x: (str(x.get("label") or ""), str(x.get("text") or "").lower()))
    return expected


def refresh_cases(file_path: Path) -> list[dict]:
    cases = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Input file must be a JSON array.")

    for case in cases:
        case["expected"] = _predict_expected(case)
    return cases


def save_cases(file_path: Path, cases: list[dict]) -> None:
    file_path.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_db(cases: list[dict], config_path: str) -> None:
    cfg = load_config_with_env(config_path)
    db_cfg = cfg["database"]
    db = DBConnector(db_cfg)
    db.connect()
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ai.prelabeler_testcases (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    input JSONB NOT NULL,
                    expected JSONB NOT NULL DEFAULT '[]',
                    strict BOOLEAN NOT NULL DEFAULT FALSE,
                    test_result JSONB NULL,
                    tested_at TIMESTAMPTZ NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            ids = [str(case.get("id") or f"case_{i}") for i, case in enumerate(cases)]
            if ids:
                cur.execute(
                    "DELETE FROM ai.prelabeler_testcases WHERE id <> ALL(%s)",
                    (ids,),
                )
            else:
                cur.execute("DELETE FROM ai.prelabeler_testcases")

            for i, case in enumerate(cases):
                case_id = str(case.get("id") or f"case_{i}")
                name = str(case.get("name") or "")
                raw_input = case.get("input")
                if isinstance(raw_input, dict):
                    input_text = str(raw_input.get("raw_address") or "").strip()
                else:
                    input_text = str(raw_input or "").strip()
                expected = case.get("expected") or []
                strict = bool(case.get("strict", False))

                cur.execute(
                    """
                    INSERT INTO ai.prelabeler_testcases
                        (id, name, input, expected, strict, test_result, tested_at, updated_at)
                    VALUES
                        (%s, %s, %s::jsonb, %s::jsonb, %s, NULL, NULL, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        input = EXCLUDED.input,
                        expected = EXCLUDED.expected,
                        strict = EXCLUDED.strict,
                        test_result = NULL,
                        tested_at = NULL,
                        updated_at = NOW()
                    """,
                    (
                        case_id,
                        name,
                        json.dumps(input_text, ensure_ascii=False),
                        json.dumps(expected, ensure_ascii=False),
                        strict,
                    ),
                )
    finally:
        db.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        default="scripts/labeling/prelabeler_labeling_cases.json",
        help="Path to labeling-case JSON file",
    )
    parser.add_argument(
        "--config",
        default="app/ai/config.yaml",
        help="Config path for DB connection",
    )
    parser.add_argument(
        "--sync-db",
        action="store_true",
        help="Upsert refreshed cases into ai.prelabeler_testcases",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    cases = refresh_cases(file_path)
    save_cases(file_path, cases)
    print(f"Refreshed {len(cases)} cases in {file_path}")

    if args.sync_db:
        sync_db(cases, args.config)
        print("Synced refreshed labeling cases to ai.prelabeler_testcases")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
