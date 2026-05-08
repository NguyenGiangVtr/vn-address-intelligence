#!/usr/bin/env python3
"""
Regression tests cho PreLabeler.

Mục tiêu: chặn lỗi tái phát khi địa chỉ nhập lặp đơn vị hành chính
gây detect nhầm STR từ tên tỉnh/huyện/xã.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.export_for_annotation import PreLabeler


def _to_label_text_set(predictions):
    return {
        (p["value"]["labels"][0], p["value"]["text"].strip().lower())
        for p in predictions
    }


def test_no_false_str_when_admin_units_are_duplicated():
    raw = "Thôn EaNguôi, xã cư né, krông búk, đắk lắk, Xã Cư Né, Huyện Krông Búk, Đắk Lắk"
    predictions = PreLabeler.predict(
        raw_address=raw,
        ward_name="Xã Cư Né",
        district_name="Huyện Krông Búk",
        province_name="Đắk Lắk",
        known_streets=set(),
    )
    label_text = _to_label_text_set(predictions)

    # Các nhãn admin đúng vẫn phải tồn tại
    assert ("WDS", "cư né") in label_text
    assert ("DST", "krông búk") in label_text
    assert ("PRO", "đắk lắk") in label_text

    # Regression guard: không được phát sinh STR từ đơn vị hành chính lặp
    assert ("STR", "đắk lắk") not in label_text


if __name__ == "__main__":
    test_no_false_str_when_admin_units_are_duplicated()
    print("OK - prelabeler regression test passed")
