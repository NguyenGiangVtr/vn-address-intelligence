"""
epoch_detector.py
=================
Temporal-Aware Address — Dual-Epoch Recognition (Chương 1.1.3, 2.4.3)

Phát hiện địa chỉ thuộc:
    - PRE_2025  : Dùng đơn vị hành chính cũ (quận, huyện, thị xã… trước cải cách 2025)
    - POST_2025 : Dùng đơn vị hành chính mới (sau Nghị quyết 2025)
    - AMBIGUOUS : Không thể xác định rõ ràng
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

# ── Pre-2025 Keywords ──────────────────────────────────────────────────────────
# Các từ khóa chỉ xuất hiện trong địa chỉ Pre-2025
PRE_2025_TYPE_KEYWORDS: List[str] = [
    "quận",
    "huyện",
    "thị xã",
    "thị trấn",
    "thị tứ",
]

# Prefix phổ biến của đơn vị Pre-2025 (có thể mở rộng từ DB)
PRE_2025_PREFIX_PATTERNS: List[str] = [
    r"\bquận\s+\d+\b",         # Quận 1, Quận 12
    r"\bquận\s+[A-Za-zÀ-ỹ]+", # Quận Bình Thạnh
    r"\bhuyện\s+[A-Za-zÀ-ỹ]+",
    r"\bthị\s+xã\s+[A-Za-zÀ-ỹ]+",
    r"\bthị\s+trấn\s+[A-Za-zÀ-ỹ]+",
]

# Post-2025: đơn vị mới
POST_2025_TYPE_KEYWORDS: List[str] = [
    "thành phố trực thuộc",
    "đặc khu",
]

CONFIDENCE_THRESHOLD = 0.6


@dataclass
class EpochDetectionResult:
    epoch: str              # PRE_2025 | POST_2025 | AMBIGUOUS
    confidence: float       # [0..1]
    matched_keywords: List[str]
    pre_score: float
    post_score: float

    def to_dict(self) -> dict:
        return {
            "epoch": self.epoch,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
            "pre_score": self.pre_score,
            "post_score": self.post_score,
        }


class EpochDetector:
    """
    Phát hiện epoch của địa chỉ (Pre-2025 / Post-2025 / Ambiguous).

    Sử dụng:
        1. Pattern matching từ khóa loại đơn vị (quận, huyện, thị xã…)
        2. Tên đơn vị hành chính từ DB (nếu db_session được cung cấp)
    """

    def __init__(self, db_session=None):
        self._db = db_session
        self._pre_unit_names: Set[str] = set()
        self._post_unit_names: Set[str] = set()
        self._loaded = False

    def load_from_db(self):
        """Load tên đơn vị hành chính từ DB theo admin_version."""
        if self._db is None or self._loaded:
            return
        try:
            from app.core.database import District, Ward
            # Pre-2025: admin_version = 1
            pre_districts = self._db.query(District.district_name).filter(
                District.admin_version == 1, District.is_current == False
            ).all()
            pre_wards = self._db.query(Ward.ward_name).filter(
                Ward.admin_version == 1, Ward.is_current == False
            ).all()
            self._pre_unit_names = {
                r[0].lower().strip() for r in pre_districts + pre_wards if r[0]
            }

            # Post-2025: admin_version = 2
            post_districts = self._db.query(District.district_name).filter(
                District.admin_version == 2
            ).all()
            post_wards = self._db.query(Ward.ward_name).filter(
                Ward.admin_version == 2
            ).all()
            self._post_unit_names = {
                r[0].lower().strip() for r in post_districts + post_wards if r[0]
            }

            self._loaded = True
            logger.info(
                "EpochDetector: loaded %d pre-2025 units, %d post-2025 units from DB",
                len(self._pre_unit_names),
                len(self._post_unit_names),
            )
        except Exception as exc:
            logger.warning("EpochDetector DB load failed: %s", exc)

    def detect(self, address: str) -> EpochDetectionResult:
        """
        Phát hiện epoch cho một địa chỉ.

        Returns EpochDetectionResult với epoch, confidence, keywords matched.
        """
        if not self._loaded and self._db:
            self.load_from_db()

        addr_lower = address.lower()
        matched: List[str] = []
        pre_score  = 0.0
        post_score = 0.0

        # 1. Kiểm tra từ khóa loại đơn vị Pre-2025
        for kw in PRE_2025_TYPE_KEYWORDS:
            if kw in addr_lower:
                pre_score += 0.4
                matched.append(kw)
                break  # Tính tối đa 1 lần cho nhóm này

        # 2. Kiểm tra regex pattern Pre-2025
        for pattern in PRE_2025_PREFIX_PATTERNS:
            if re.search(pattern, addr_lower):
                pre_score = min(pre_score + 0.2, 1.0)
                break

        # 3. Kiểm tra từ khóa Post-2025
        for kw in POST_2025_TYPE_KEYWORDS:
            if kw in addr_lower:
                post_score += 0.4
                matched.append(kw)
                break

        # 4. So khớp tên đơn vị từ DB
        if self._pre_unit_names or self._post_unit_names:
            words = set(re.sub(r"[,.]", " ", addr_lower).split())
            # Bigrams + trigrams để khớp tên đơn vị nhiều từ
            tokens = addr_lower.split()
            ngrams = set(tokens)
            ngrams |= {" ".join(tokens[i:i+2]) for i in range(len(tokens)-1)}
            ngrams |= {" ".join(tokens[i:i+3]) for i in range(len(tokens)-2)}

            pre_hits  = ngrams & self._pre_unit_names
            post_hits = ngrams & self._post_unit_names

            if pre_hits:
                pre_score  = min(pre_score + 0.3 * len(pre_hits), 1.0)
                matched.extend(list(pre_hits))
            if post_hits:
                post_score = min(post_score + 0.3 * len(post_hits), 1.0)
                matched.extend(list(post_hits))

        # 5. Quyết định epoch
        pre_score  = round(min(pre_score,  1.0), 4)
        post_score = round(min(post_score, 1.0), 4)

        if pre_score >= CONFIDENCE_THRESHOLD and pre_score > post_score:
            epoch = "PRE_2025"
            confidence = pre_score
        elif post_score >= CONFIDENCE_THRESHOLD and post_score > pre_score:
            epoch = "POST_2025"
            confidence = post_score
        elif pre_score == 0.0 and post_score == 0.0:
            epoch = "AMBIGUOUS"
            confidence = 0.0
        else:
            epoch = "AMBIGUOUS"
            confidence = max(pre_score, post_score)

        return EpochDetectionResult(
            epoch=epoch,
            confidence=confidence,
            matched_keywords=list(set(matched)),
            pre_score=pre_score,
            post_score=post_score,
        )

    def convert_pre_to_post(
        self,
        address: str,
        province_id: Optional[int] = None,
    ) -> dict:
        """
        Chuyển đổi địa chỉ Pre-2025 → Post-2025.
        Dùng mat.ward_mapping để tra cứu mapping.

        Returns dict với 'converted_address', 'mapping_applied', 'confidence'.
        """
        if self._db is None:
            return {
                "converted_address": address,
                "mapping_applied": False,
                "confidence": 0.0,
                "message": "DB session không có sẵn",
            }

        try:
            from app.core.database import WardMapping, Ward, District, Province

            # Tìm từ WardMapping có is_deleted=False
            mappings = (
                self._db.query(WardMapping)
                .filter(WardMapping.is_deleted == False)
                .order_by(WardMapping.effective_date_from.desc())
                .all()
            )

            addr_lower = address.lower()
            applied = []

            for m in mappings:
                # Tra cứu tên ward cũ
                old_ward = self._db.query(Ward).filter(
                    Ward.ward_id == m.ward_id_old
                ).first()
                new_ward = self._db.query(Ward).filter(
                    Ward.ward_id == m.ward_id_new
                ).first()

                if old_ward and new_ward and old_ward.ward_name:
                    old_name = old_ward.ward_name.lower()
                    if old_name in addr_lower and old_name != new_ward.ward_name.lower():
                        address = re.sub(
                            re.escape(old_ward.ward_name),
                            new_ward.ward_name,
                            address,
                            flags=re.IGNORECASE,
                        )
                        applied.append(
                            f"{old_ward.ward_name} → {new_ward.ward_name}"
                        )

            return {
                "converted_address": address,
                "mapping_applied": len(applied) > 0,
                "mappings_used": applied,
                "confidence": 0.85 if applied else 0.3,
            }

        except Exception as exc:
            logger.error("convert_pre_to_post error: %s", exc)
            return {
                "converted_address": address,
                "mapping_applied": False,
                "confidence": 0.0,
                "error": str(exc),
            }
