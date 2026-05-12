"""
acs_calculator.py
=================
Address Confidence Score (ACS) Calculator — Chương 2.4.5

Tính toán điểm tin cậy tổng hợp cho mỗi địa chỉ sau khi parse:

    ACS = w1 * s_text + w2 * s_sem + w3 * v_hierarchy + w4 * v_temporal

Bảng quyết định:
    ≥ 0.90 → AUTO_ACCEPT
    0.70–0.89 → AUTO_CONVERT
    0.50–0.69 → SUGGEST
    < 0.50 → REJECT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Weights ────────────────────────────────────────────────────────────────────
W_TEXT      = 0.30   # Similarity văn bản (levenshtein / token overlap)
W_SEM       = 0.35   # Semantic similarity (Siamese mGTE score)
W_HIERARCHY = 0.25   # Hierarchy validation (Phường ∈ Huyện ∈ Tỉnh)
W_TEMPORAL  = 0.10   # Temporal weight (phạt admin version cũ)
W_GEO       = 0.10   # Độ tin cậy geolocation (nếu có)

# ── Decision thresholds ────────────────────────────────────────────────────────
THRESHOLD_AUTO_ACCEPT  = 0.90
THRESHOLD_AUTO_CONVERT = 0.70
THRESHOLD_SUGGEST      = 0.50


@dataclass
class ACSComponents:
    """Các thành phần điểm số chi tiết của ACS."""
    s_text:      float = 0.0   # Text similarity [0..1]
    s_sem:       float = 0.0   # Semantic similarity [0..1]
    v_hierarchy: float = 0.0   # Hierarchy validity [0..1]
    v_temporal:  float = 1.0   # Temporal weight [0..1] — default full score
    v_geo:       float = 0.5   # Geospatial validity [0..1]
    acs_score:   float = 0.0   # Weighted sum
    acs_decision: str  = "REJECT"

    def to_dict(self) -> dict:
        return asdict(self)


class ACSCalculator:
    """
    Tính Address Confidence Score cho một kết quả parse địa chỉ.

    Parameters
    ----------
    db_session : SQLAlchemy Session
        Dùng để validate hierarchy trong mat.* tables.
    """

    def __init__(self, db_session=None):
        self._db = db_session

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def compute(
        self,
        raw_address: str,
        standardized_address: str,
        semantic_score: float,
        province_id: Optional[int] = None,
        district_id: Optional[int] = None,
        ward_id: Optional[int] = None,
        admin_version: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> ACSComponents:
        """
        Tính ACS đầy đủ.

        Parameters
        ----------
        raw_address         : Địa chỉ thô gốc
        standardized_address: Địa chỉ sau khi chuẩn hóa
        semantic_score      : Cosine similarity từ Siamese mGTE [0..1]
        province_id / district_id / ward_id : ID đơn vị hành chính (nếu có)
        admin_version       : Phiên bản hành chính (1 = Pre-2025, 2 = Post-2025)
        """
        comp = ACSComponents()

        comp.s_text      = self._compute_text_similarity(raw_address, standardized_address)
        comp.s_sem       = float(max(0.0, min(1.0, semantic_score)))
        comp.v_hierarchy = self.validate_hierarchy(province_id, district_id, ward_id)
        comp.v_temporal  = self.compute_temporal_weight(admin_version)
        comp.v_geo       = self.compute_geo_weight(latitude=latitude, longitude=longitude)

        comp.acs_score = (
            (W_TEXT      * comp.s_text)
            + (W_SEM       * comp.s_sem)
            + (W_HIERARCHY * comp.v_hierarchy)
            + (W_TEMPORAL  * comp.v_temporal)
            + (W_GEO       * comp.v_geo)
        )
        comp.acs_score   = round(comp.acs_score, 4)
        comp.acs_decision = self.get_decision(comp.acs_score)

        return comp

    # ──────────────────────────────────────────────────────────────────────────
    # Subcomponents
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_text_similarity(self, raw: str, standardized: str) -> float:
        """Token overlap Jaccard giữa địa chỉ gốc và địa chỉ chuẩn hóa."""
        if not raw or not standardized:
            return 0.0
        tokens_raw = set(_tokenize(raw))
        tokens_std = set(_tokenize(standardized))
        if not tokens_raw:
            return 0.0
        intersection = tokens_raw & tokens_std
        union = tokens_raw | tokens_std
        return len(intersection) / len(union) if union else 0.0

    def validate_hierarchy(
        self,
        province_id: Optional[int],
        district_id: Optional[int],
        ward_id: Optional[int],
    ) -> float:
        """
        Kiểm tra: Phường ∈ Huyện ∈ Tỉnh trong mat.* tables.

        Trả về:
            1.0 — hierarchy hợp lệ hoặc không có đủ ID để kiểm tra
            0.5 — chỉ kiểm tra được một phần (thiếu ID)
            0.0 — hierarchy KHÔNG hợp lệ
        """
        if self._db is None:
            return 1.0  # Không có DB session → bỏ qua kiểm tra

        from app.core.database import District, Ward

        try:
            checks_passed = 0
            checks_total  = 0

            # Phường ∈ Huyện
            if ward_id and district_id:
                checks_total += 1
                ward = self._db.query(Ward).filter(
                    Ward.ward_id == ward_id,
                    Ward.district_id == district_id,
                    Ward.is_active == True,
                ).first()
                if ward:
                    checks_passed += 1

            # Huyện ∈ Tỉnh
            if district_id and province_id:
                checks_total += 1
                district = self._db.query(District).filter(
                    District.district_id == district_id,
                    District.province_id == province_id,
                    District.is_active == True,
                ).first()
                if district:
                    checks_passed += 1

            if checks_total == 0:
                return 0.5  # Không đủ thông tin để validate đầy đủ

            return checks_passed / checks_total

        except Exception as exc:
            logger.warning("Hierarchy validation error: %s", exc)
            return 0.5

    def compute_temporal_weight(self, admin_version: Optional[int]) -> float:
        """
        Phạt nhẹ địa chỉ dùng đơn vị hành chính phiên bản cũ (Pre-2025).

        admin_version=1 → Pre-2025  → phạt 0.2 điểm
        admin_version=2 → Post-2025 → không phạt
        None            → không xác định → phạt nhẹ 0.1 điểm
        """
        if admin_version is None:
            return 0.9
        if admin_version >= 2:
            return 1.0
        return 0.8  # Pre-2025 penalty

    @staticmethod
    def compute_geo_weight(latitude: Optional[float], longitude: Optional[float]) -> float:
        """
        Geospatial confidence based on coordinate availability and validity.
        """
        if latitude is None or longitude is None:
            return 0.5
        if not (-90.0 <= float(latitude) <= 90.0 and -180.0 <= float(longitude) <= 180.0):
            return 0.0
        # For Vietnam-focused pipeline, soft preference in expected bounding box.
        if 8.0 <= float(latitude) <= 24.0 and 102.0 <= float(longitude) <= 110.0:
            return 1.0
        return 0.7

    @staticmethod
    def get_decision(acs_score: float) -> str:
        """
        Bảng quyết định ACS:
            ≥ 0.90 → AUTO_ACCEPT
            0.70–0.89 → AUTO_CONVERT
            0.50–0.69 → SUGGEST
            < 0.50 → REJECT
        """
        if acs_score >= THRESHOLD_AUTO_ACCEPT:
            return "AUTO_ACCEPT"
        if acs_score >= THRESHOLD_AUTO_CONVERT:
            return "AUTO_CONVERT"
        if acs_score >= THRESHOLD_SUGGEST:
            return "SUGGEST"
        return "REJECT"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Tách từ đơn giản: lowercase + loại bỏ dấu câu."""
    import re
    return re.sub(r"[^\w\s]", " ", text.lower()).split()
