"""
spatial_mismatch.py
===================
Spatial Mismatch Analysis Pipeline (G3 — Chương 3.4)

Phân tích sai lệch địa lý từ dữ liệu đơn hàng CSV:
    - Load CSV chứa cột lat, lon, ward_id (hoặc tương đương)
    - Kiểm tra từng điểm: GPS có khớp với đơn vị hành chính khai báo không?
    - Áp dụng 3 chiến lược sửa lỗi: Buffer Union → Concave Hull → Edge Inject
    - Xuất báo cáo mismatch
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class MismatchRecord:
    row_index: int
    raw_address: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    declared_ward_id: Optional[int]
    declared_ward_name: Optional[str]
    detected_ward_id: Optional[int]
    detected_ward_name: Optional[str]
    correction_method: str  # polygon | buffer_union | concave_hull | edge_inject | none
    is_mismatch: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MismatchReport:
    total_rows: int = 0
    matched: int = 0
    mismatched: int = 0
    corrected: int = 0
    uncorrectable: int = 0
    records: List[MismatchRecord] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "total_rows":    self.total_rows,
            "matched":       self.matched,
            "mismatched":    self.mismatched,
            "corrected":     self.corrected,
            "uncorrectable": self.uncorrectable,
            "accuracy_pct":  round(self.matched / self.total_rows * 100, 2) if self.total_rows else 0,
            "correction_rate_pct": round(self.corrected / self.mismatched * 100, 2) if self.mismatched else 0,
        }


class SpatialMismatchPipeline:
    """
    Pipeline phân tích sai lệch địa lý.

    Sử dụng 3 chiến lược theo thứ tự ưu tiên:
        1. Buffer Union  — mở rộng polygon
        2. Concave Hull — tái tạo polygon từ đám mây điểm
        3. Edge Inject  — đồ thị quan hệ hành chính
    """

    def __init__(self, db_session):
        self._db = db_session
        self._has_postgis: Optional[bool] = None

    def _check_postgis(self) -> bool:
        if self._has_postgis is not None:
            return self._has_postgis
        try:
            from sqlalchemy import text
            result = self._db.execute(
                text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'postgis'")
            ).scalar()
            self._has_postgis = (result or 0) > 0
        except Exception:
            self._has_postgis = False
        return self._has_postgis

    def analyze_csv(
        self,
        csv_content: str,
        lat_col: str = "lat",
        lon_col: str = "lon",
        ward_id_col: str = "ward_id",
        ward_name_col: str = "ward_name",
        address_col: str = "raw_address",
    ) -> MismatchReport:
        """
        Phân tích CSV và phát hiện sai lệch.

        Parameters
        ----------
        csv_content  : Nội dung CSV dạng string (UTF-8)
        lat_col      : Tên cột latitude
        lon_col      : Tên cột longitude
        ward_id_col  : Tên cột ward_id (ID phường/xã khai báo)
        ward_name_col: Tên cột ward_name
        address_col  : Tên cột địa chỉ thô

        Returns
        -------
        MismatchReport với đầy đủ records và summary.
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        report = MismatchReport()
        has_postgis = self._check_postgis()

        for i, row in enumerate(reader):
            report.total_rows += 1

            try:
                lat = float(row.get(lat_col) or 0) or None
                lon = float(row.get(lon_col) or 0) or None
                declared_ward_id = int(row.get(ward_id_col) or 0) or None
                declared_ward_name = row.get(ward_name_col)
                raw_address = row.get(address_col)
            except (ValueError, TypeError):
                report.uncorrectable += 1
                continue

            if lat is None or lon is None or declared_ward_id is None:
                report.uncorrectable += 1
                continue

            detected_unit_id, detected_unit_name, method = self._detect_unit(
                lat, lon, has_postgis
            )

            is_mismatch = (
                detected_unit_id is not None
                and detected_unit_id != declared_ward_id
            )

            if not is_mismatch:
                report.matched += 1
            else:
                report.mismatched += 1
                # Thử sửa lỗi
                corrected = self._apply_correction_strategies(
                    lat, lon, declared_ward_id
                )
                if corrected:
                    detected_unit_id   = corrected.get("unit_id", detected_unit_id)
                    detected_unit_name = corrected.get("unit_name", detected_unit_name)
                    method = corrected.get("method", method)
                    report.corrected += 1

            report.records.append(
                MismatchRecord(
                    row_index=i,
                    raw_address=raw_address,
                    lat=lat,
                    lon=lon,
                    declared_ward_id=declared_ward_id,
                    declared_ward_name=declared_ward_name,
                    detected_ward_id=detected_unit_id,
                    detected_ward_name=detected_unit_name,
                    correction_method=method,
                    is_mismatch=is_mismatch,
                )
            )

        report.uncorrectable = report.mismatched - report.corrected
        return report

    def _detect_unit(
        self, lat: float, lon: float, has_postgis: bool
    ):
        """Phát hiện đơn vị hành chính từ tọa độ GPS."""
        if not has_postgis:
            return None, None, "none"

        from sqlalchemy import text
        try:
            sql = text("""
                SELECT unit_id, unit_name
                FROM mat.area_polygon
                WHERE unit_level = 'ward'
                  AND ST_Contains(
                      ST_SetSRID(ST_GeomFromGeoJSON(geojson::text), 4326),
                      ST_SetSRID(ST_Point(:lon, :lat), 4326)
                  )
                LIMIT 1
            """)
            row = self._db.execute(sql, {"lat": lat, "lon": lon}).fetchone()
            if row:
                return row[0], row[1], "polygon"
        except Exception as exc:
            logger.warning("_detect_unit error: %s", exc)

        return None, None, "none"

    def _apply_correction_strategies(
        self, lat: float, lon: float, declared_ward_id: int
    ) -> Optional[Dict[str, Any]]:
        """Áp dụng 3 chiến lược sửa lỗi theo thứ tự."""
        # Chiến lược 1: Buffer Union
        try:
            from app.geometry.buffer_union import adaptive_buffer_lookup
            result = adaptive_buffer_lookup(self._db, lat, lon, "ward")
            if result and result.get("unit_id") == declared_ward_id:
                return result
        except Exception as exc:
            logger.debug("Buffer union strategy failed: %s", exc)

        # Chiến lược 2: Concave Hull (chỉ dùng khi polygon chưa có/sai)
        try:
            from app.geometry.concave_hull import build_concave_hull_from_points
            hull = build_concave_hull_from_points(self._db, declared_ward_id, "ward")
            if hull:
                return {"unit_id": declared_ward_id, "method": "concave_hull"}
        except Exception as exc:
            logger.debug("Concave hull strategy failed: %s", exc)

        # Chiến lược 3: Edge Inject
        try:
            from app.geometry.edge_inject import edge_inject_lookup
            result = edge_inject_lookup(self._db, lat, lon, declared_ward_id, "ward")
            if result:
                return result
        except Exception as exc:
            logger.debug("Edge inject strategy failed: %s", exc)

        return None
