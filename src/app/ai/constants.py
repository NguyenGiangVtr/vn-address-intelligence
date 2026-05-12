"""
constants.py
============
Định nghĩa tập trung các hằng số dùng chung cho toàn bộ module AI.
Giúp đồng bộ nhãn (Labels) giữa Export, Training và Inference.

SINGLE SOURCE OF TRUTH cho:
- Danh sách nhãn NER (NER_LABELS).
- Bộ tiền tố đơn vị hành chính WDS/DST/PRO (ADMIN_PREFIX_ALTERNATIVES,
  ADMIN_PRESENCE_ALTERNATIVES) — dùng chung cho predictor (PreLabeler)
  và validator (prelabeler_labeling_service).
"""

# ──────────────────────────────────────────────────────────────────────────────
# Bộ tiền tố đơn vị hành chính (CANONICAL — không khai báo lại ở nơi khác)
# ──────────────────────────────────────────────────────────────────────────────
# Lưu ý "Thành phố" có thể là PRO (TP trực thuộc TW) hoặc DST (TP thuộc tỉnh).
# Vì vậy nó xuất hiện trong cả ADMIN_PREFIX_ALTERNATIVES["DST"] và ["PRO"].
ADMIN_PREFIX_ALTERNATIVES = {
    "WDS": r"Phường|Xã|Thị trấn|P\.|X\.",
    "DST": r"Quận|Huyện|Thị xã|Thành phố|Q\.|H\.",
    "PRO": r"Tỉnh|Thành phố|TP\.?",
}

# Pattern dùng để KIỂM TRA SỰ HIỆN DIỆN của một admin level trong raw text.
# PRO ở đây chủ động loại bỏ "Thành phố" để tránh trigger nhầm khi raw chứa
# cụm "Thành phố Thủ Đức" (vốn là DST). Không trùng với ADMIN_PREFIX_ALTERNATIVES
# dù dùng chung vocabulary cơ sở — đây là biến thể có chủ đích.
ADMIN_PRESENCE_ALTERNATIVES = {
    "WDS": ADMIN_PREFIX_ALTERNATIVES["WDS"],
    "DST": ADMIN_PREFIX_ALTERNATIVES["DST"],
    "PRO": r"Tỉnh|TP\.?",
}

# Union vocabulary: TẤT CẢ tiền tố admin (WDS+DST+PRO) dạng optional-dot.
# Dùng cho các heuristic noi bo trong predictor cần nhận diện "bất kỳ admin prefix nào".
ADMIN_ALL_PREFIXES_ALT = (
    r"Thành phố|Tỉnh|Quận|Huyện|Thị xã|Phường|Xã|Thị trấn|"
    r"TP\.?|Q\.?|H\.?|P\.?|X\.?"
)


def admin_prefix_anchored_pattern(label: str) -> str:
    """Tra ve regex `(?i)^(<alts>)\\s+` cho label admin (WDS/DST/PRO)."""
    alts = ADMIN_PREFIX_ALTERNATIVES.get(label)
    if not alts:
        return ""
    return rf"(?i)^({alts})\s+"


def admin_presence_pattern(label: str) -> str:
    """Tra ve regex `(?i)\\b(<alts>)\\s+` de kiem tra hien dien admin trong raw text."""
    alts = ADMIN_PRESENCE_ALTERNATIVES.get(label)
    if not alts:
        return ""
    return rf"(?i)\b({alts})\s+"


# 1. Định nghĩa danh sách nhãn NER chuẩn
# Mỗi nhãn: value (mã, hiển thị trên Label Studio), color, hotkey (tuỳ chọn: alias, hint)
NER_LABELS = [
    {"value": "PCD", "color": "#f032e6", "hotkey": "0"},
    {"value": "BLD", "color": "#f58231", "hotkey": "1"},
    {"value": "POI", "color": "#911eb4", "hotkey": "2"},
    {"value": "ALY", "color": "#4363d8", "hotkey": "3"},
    {"value": "NUM", "color": "#e6194B", "hotkey": "4"},
    {"value": "STR", "color": "#3cb44b", "hotkey": "5"},
    {"value": "NHB", "color": "#469990", "hotkey": "6"},
    {"value": "WDS", "color": "#ffe119", "hotkey": "7"},
    {"value": "DST", "color": "#800000", "hotkey": "8"},
    {"value": "PRO", "color": "#38bdf8", "hotkey": "9"},
    
]

def get_ner_label_list():
    """
    Tạo danh sách nhãn theo định dạng BIO dùng cho huấn luyện mô hình.
    Kết quả: ["O", "B-NUM", "I-NUM", "B-STR", "I-STR", ...]
    """
    bio_list = ["O"]
    for label in NER_LABELS:
        val = label["value"]
        bio_list.append(f"B-{val}")
        bio_list.append(f"I-{val}")
    return bio_list

def get_label_count():
    """Trả về số lượng thực thể (không tính nhãn O)."""
    return len(NER_LABELS)
