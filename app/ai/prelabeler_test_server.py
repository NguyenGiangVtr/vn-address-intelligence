"""
prelabeler_test_server.py
=========================
Flask API server phục vụ UI kiểm thử PreLabeler.

Chạy:
    python app/ai/prelabeler_test_server.py

Mở trình duyệt: http://localhost:5050
"""

import sys
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from app.ai.export_for_annotation import PreLabeler

app = Flask(__name__)
CORS(app)

# Lưu test cases vào file JSON bên cạnh script này
TESTCASE_FILE = Path(__file__).parent / "prelabeler_testcases.json"


def load_testcases():
    if TESTCASE_FILE.exists():
        with open(TESTCASE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_testcases(cases):
    with open(TESTCASE_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    ui_file = Path(__file__).parent / "prelabeler_test_ui.html"
    return send_from_directory(str(ui_file.parent), ui_file.name)


@app.route("/api/testcases", methods=["GET"])
def get_testcases():
    return jsonify(load_testcases())


@app.route("/api/testcases", methods=["POST"])
def save_testcases_api():
    data = request.json
    save_testcases(data)
    return jsonify({"ok": True})


@app.route("/api/run", methods=["POST"])
def run_tests():
    """Chạy PreLabeler cho từng test case và so sánh với expected."""
    body = request.json
    cases = body.get("cases", [])
    results = []

    for case in cases:
        inp = case.get("input", {})
        expected = case.get("expected", [])  # [{"label": "STR", "text": "Tam Bình"}]

        try:
            predictions = PreLabeler.predict(
                raw_address=inp.get("raw_address", ""),
                ward_name=inp.get("ward_name") or None,
                district_name=inp.get("district_name") or None,
                province_name=inp.get("province_name") or None,
            )
        except Exception as e:
            results.append({
                "id": case.get("id"),
                "passed": False,
                "error": str(e),
                "actual": [],
                "expected": expected,
                "details": []
            })
            continue

        # Chuẩn hoá actual thành list {label, text}
        actual = [
            {"label": p["value"]["labels"][0], "text": p["value"]["text"]}
            for p in predictions
        ]

        # So sánh: mỗi expected item phải tìm thấy trong actual (label + text khớp case-insensitive)
        details = []
        all_passed = True
        for exp in expected:
            found = any(
                a["label"] == exp["label"] and a["text"].strip().lower() == exp["text"].strip().lower()
                for a in actual
            )
            details.append({"expected": exp, "found": found})
            if not found:
                all_passed = False

        # Kiểm tra không có nhãn "rogue" (actual có nhãn mà expected không mong muốn)
        unexpected = []
        if case.get("strict", False):
            for act in actual:
                match = any(
                    e["label"] == act["label"] and e["text"].strip().lower() == act["text"].strip().lower()
                    for e in expected
                )
                if not match:
                    unexpected.append(act)
                    all_passed = False

        results.append({
            "id": case.get("id"),
            "passed": all_passed,
            "actual": actual,
            "expected": expected,
            "details": details,
            "unexpected": unexpected,
        })

    return jsonify(results)


if __name__ == "__main__":
    print(f"\n  PreLabeler Test Server")
    print(f"  UI: http://localhost:5050")
    print(f"  Testcases: {TESTCASE_FILE}\n")
    app.run(host="0.0.0.0", port=5050, debug=True)
