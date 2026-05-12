#!/usr/bin/env python3
"""
Smoke + contract tests cho FastAPI (đường dẫn /api/*).

Mục tiêu:
- Bắt lỗi kiểu UI gọi POST /prelabeler-cases/run thiếu wrapper `cases` hoặc sai shape.
- Kiểm tra "đối chiếu toàn bộ mẫu": payload trùng logic `normalizeCaseForApi` trong ui/app.js.

Chạy nhanh (không cần DB cho phần lớn test — startup DB đã tắt bằng monkeypatch):
  python -m pytest scripts/test/test_api_full.py -v

Chạy kèm toàn bộ mẫu từ JSON (lâu hơn, ~330 case):
  set VNAI_PRELABELER_RUN_FULL_SUITE=1
  python -m pytest scripts/test/test_api_full.py -v -k full_suite
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

import _bootstrap_import_paths  # noqa: E402

_bootstrap_import_paths.install()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_case_for_api(c: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    """Mirror ui/app.js `normalizeCaseForApi` (giữ contract với POST /prelabeler-cases/run)."""
    raw_in = c.get("input")
    if isinstance(raw_in, str):
        inp = raw_in
    elif isinstance(raw_in, dict):
        inp = str(raw_in.get("raw_address") or "").strip()
    else:
        inp = str(raw_in if raw_in is not None else "")
    expected_raw = c.get("expected") if isinstance(c.get("expected"), list) else []
    expected: list[dict[str, str]] = []
    for e in expected_raw:
        if not isinstance(e, dict):
            continue
        label = str(e.get("label") or "").strip().upper()
        text = str(e.get("text") or "").strip()
        if label and text:
            expected.append({"label": label, "text": text})
    out: dict[str, Any] = {
        "id": str(c.get("id") or f"case_{idx}"),
        "name": str(c.get("name") or ""),
        "input": inp,
        "note": str(c.get("note") or ""),
        "expected": expected,
        "strict": c.get("strict") is not False,
    }
    md = c.get("meta")
    if isinstance(md, dict) and any(
        md.get(k) is not None and str(md.get(k) or "").strip()
        for k in ("ward_name", "district_name", "province_name")
    ):
        out["meta"] = {
            "ward_name": (
                str(md["ward_name"]).strip()
                if md.get("ward_name") is not None and str(md.get("ward_name") or "").strip()
                else None
            ),
            "district_name": (
                str(md["district_name"]).strip()
                if md.get("district_name") is not None and str(md.get("district_name") or "").strip()
                else None
            ),
            "province_name": (
                str(md["province_name"]).strip()
                if md.get("province_name") is not None and str(md.get("province_name") or "").strip()
                else None
            ),
        }
    return out


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    """TestClient: không chạy startup kết nối DB; auth luôn pass."""
    import app.api.server as srv
    from app.api.deps import get_current_user

    monkeypatch.setattr(srv, "_ensure_auth_user_table", lambda: None)
    monkeypatch.setattr(srv, "_start_background_model_loading", lambda: None)

    def _override_user() -> str:
        return "pytest-api"

    srv.app.dependency_overrides[get_current_user] = _override_user
    from fastapi.testclient import TestClient

    with TestClient(srv.app) as c:
        yield c
    srv.app.dependency_overrides.clear()


def test_public_health_and_ner_labels(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

    r2 = client.get("/api/config/ner-labels")
    assert r2.status_code == 200
    body = r2.json()
    assert isinstance(body.get("labels"), list)
    assert len(body["labels"]) > 0


def test_openapi_lists_prelabeler_run(client):
    schema = client.app.openapi()
    paths = schema.get("paths") or {}
    assert "/api/prelabeler-cases/run" in paths
    methods = paths["/api/prelabeler-cases/run"]
    assert "post" in methods


def test_prelabeler_run_requires_cases_wrapper(client):
    """Thiếu key `cases` → FastAPI 422 (thường bị nhầm khi gọi tay)."""
    r = client.post(
        "/api/prelabeler-cases/run",
        json=[{"id": "x", "input": "a", "expected": []}],
    )
    assert r.status_code == 422


def test_prelabeler_run_single_ok(client):
    payload = {
        "cases": [
            normalize_case_for_api(
                {
                    "id": "api_test_one",
                    "input": "45 Nguyễn Hoành, Phường Vĩnh Trường, Nha Trang, Khánh Hòa",
                    "expected": [
                        {"label": "STR", "text": "Nguyễn Hoành"},
                        {"label": "WDS", "text": "Phường Vĩnh Trường"},
                        {"label": "PRO", "text": "Khánh Hòa"},
                    ],
                    "strict": False,
                },
                0,
            )
        ]
    }
    r = client.post("/api/prelabeler-cases/run", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    row = data[0]
    assert row.get("id") == "api_test_one"
    assert "passed" in row
    assert isinstance(row.get("actual"), list)


def test_prelabeler_run_dict_input_like_db_row(client):
    """GET /prelabeler-cases có thể trả input dạng object; /run phải nhận raw_address đúng (đồng bộ UI)."""
    addr = "45 Nguyễn Hoành, Phường Vĩnh Trường, Nha Trang, Khánh Hòa"
    payload = {
        "cases": [
            normalize_case_for_api(
                {
                    "id": "api_dict_input",
                    "input": {"raw_address": addr, "ward_name": "", "district_name": "", "province_name": ""},
                    "expected": [
                        {"label": "STR", "text": "Nguyễn Hoành"},
                        {"label": "WDS", "text": "Phường Vĩnh Trường"},
                        {"label": "PRO", "text": "Khánh Hòa"},
                    ],
                    "strict": False,
                },
                0,
            )
        ]
    }
    r = client.post("/api/prelabeler-cases/run", json=payload)
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row.get("id") == "api_dict_input"
    assert "error" not in row or not row.get("error")
    assert isinstance(row.get("actual"), list)
    assert len(row.get("actual") or []) > 0


def test_prelabeler_run_bulk_like_ui(client):
    """Giả lập nút "đối chiếu all": nhiều case, cùng shape UI."""
    raw_cases = [
        {
            "id": "bulk_a",
            "input": "5756+G3 Hàm Thuận Bắc, Bình Thuận",
            "expected": [
                {"label": "DST", "text": "Hàm Thuận Bắc"},
                {"label": "PRO", "text": "Bình Thuận"},
                {"label": "PCD", "text": "5756+G3"},
            ],
            "strict": False,
        },
        {
            "id": "bulk_b",
            "input": "Số 1 Trần Hưng Đạo, Quận 1, TP. Hồ Chí Minh",
            "expected": [
                {"label": "NUM", "text": "Số 1"},
                {"label": "STR", "text": "Trần Hưng Đạo"},
                {"label": "DST", "text": "Quận 1"},
                {"label": "PRO", "text": "TP. Hồ Chí Minh"},
            ],
            "strict": False,
        },
    ]
    payload = {"cases": [normalize_case_for_api(c, i) for i, c in enumerate(raw_cases)]}
    r = client.post("/api/prelabeler-cases/run", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 2
    ids = {row["id"] for row in data}
    assert ids == {"bulk_a", "bulk_b"}


@pytest.mark.skipif(
    not os.environ.get("VNAI_PRELABELER_RUN_FULL_SUITE"),
    reason="Set VNAI_PRELABELER_RUN_FULL_SUITE=1 to run full JSON suite (~330 cases).",
)
def test_prelabeler_run_full_suite(client):
    path = _repo_root() / "scripts" / "labeling" / "prelabeler_labeling_cases.json"
    assert path.is_file(), f"Missing {path}"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(cases, list) and len(cases) > 0
    payload = {"cases": [normalize_case_for_api(c, i) for i, c in enumerate(cases)]}
    r = client.post("/api/prelabeler-cases/run", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == len(cases)
    for row in data:
        assert "id" in row and "passed" in row


def test_auth_enforced_without_override(monkeypatch: pytest.MonkeyPatch):
    """Sau khi xóa override, GET /prelabeler-cases phải 401 nếu không Bearer."""
    import app.api.server as srv
    from app.api.deps import get_current_user

    monkeypatch.setattr(srv, "_ensure_auth_user_table", lambda: None)
    monkeypatch.setattr(srv, "_start_background_model_loading", lambda: None)
    srv.app.dependency_overrides.pop(get_current_user, None)

    from fastapi.testclient import TestClient

    with TestClient(srv.app) as c:
        r = c.get("/api/prelabeler-cases")
    assert r.status_code == 401
