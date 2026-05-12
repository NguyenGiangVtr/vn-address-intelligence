#!/usr/bin/env python3
"""
Regression tests cho PreLabeler.

Muc tieu: chan loi tai phat khi dia chi nhap lap don vi hanh chinh
gay detect nham STR tu ten tinh/huyen/xa.

Tuan thu rule "Type + Name" cho admin labels (WDS/DST/PRO).
"""

import sys
from pathlib import Path

for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
import _bootstrap_import_paths  # noqa: E402

_bootstrap_import_paths.install()

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

    # Cac nhan admin dung phai ton tai (giu Type + Name).
    assert ("WDS", "xã cư né") in label_text
    assert ("DST", "huyện krông búk") in label_text
    assert ("PRO", "đắk lắk") in label_text

    # Regression guard: khong duoc phat sinh STR tu don vi hanh chinh lap.
    assert ("STR", "đắk lắk") not in label_text
    assert ("STR", "krông búk") not in label_text
    assert ("STR", "cư né") not in label_text


if __name__ == "__main__":
    test_no_false_str_when_admin_units_are_duplicated()
    print("OK - prelabeler regression test passed")
