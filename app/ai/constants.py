"""
constants.py
============
Định nghĩa tập trung các hằng số dùng chung cho toàn bộ module AI.
Giúp đồng bộ nhãn (Labels) giữa Export, Training và Inference.
"""

# 1. Định nghĩa danh sách nhãn NER chuẩn
# Mỗi nhãn bao gồm: value (mã), text (hiển thị), color (màu trên UI), hotkey (phím tắt)
NER_LABELS = [
    {"value": "PCD", "text": "Plus Code", "color": "#f032e6", "hotkey": "0"},
    {"value": "BLD", "text": "Tòa nhà/Chung cư", "color": "#f58231", "hotkey": "1"},
    {"value": "POI", "text": "Địa danh/Mốc/Địa điểm / Cửa hàng", "color": "#911eb4", "hotkey": "2"},
    {"value": "ALY", "text": "Hẻm/Ngõ", "color": "#4363d8", "hotkey": "3"},
    {"value": "NUM", "text": "Số nhà / Lô / P.", "color": "#e6194B", "hotkey": "4"},
    {"value": "STR", "text": "Tên đường", "color": "#3cb44b", "hotkey": "5"},
    {"value": "NHB", "text": "Khu phố/Thôn/Ấp/Làng/Xóm", "color": "#469990", "hotkey": "6"},
    {"value": "WDS", "text": "Phường/Xã", "color": "#ffe119", "hotkey": "7"},
    {"value": "DST", "text": "Quận/Huyện", "color": "#800000", "hotkey": "8"},
    {"value": "PRO", "text": "Tỉnh/Thành phố", "color": "#000075", "hotkey": "9"},
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
