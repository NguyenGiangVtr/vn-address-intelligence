"""
constants.py
============
Định nghĩa tập trung các hằng số dùng chung cho toàn bộ module AI.
Giúp đồng bộ nhãn (Labels) giữa Export, Training và Inference.
"""

# 1. Định nghĩa danh sách nhãn NER chuẩn
# Mỗi nhãn: value (mã, hiển thị trên Label Studio), color, hotkey (tuỳ chọn: alias, hint)
NER_LABELS = [
    {"value": "NUM", "color": "#e6194B", "hotkey": "1"},
    {"value": "STR", "color": "#3cb44b", "hotkey": "2"},
    {"value": "WDS", "color": "#ffe119", "hotkey": "3"},
    {"value": "DST", "color": "#800000", "hotkey": "4"},
    {"value": "PRO", "color": "#38bdf8", "hotkey": "5"},
    {"value": "NHB", "color": "#469990", "hotkey": "6"},
    {"value": "BLD", "color": "#f58231", "hotkey": "7"},
    {"value": "POI", "color": "#911eb4", "hotkey": "8"},
    {"value": "FLR", "color": "#4363d8", "hotkey": "9"},
    {"value": "RM", "color": "#f032e6", "hotkey": "0"},
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
