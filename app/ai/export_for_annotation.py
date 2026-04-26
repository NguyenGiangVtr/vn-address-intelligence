"""
export_for_annotation.py
========================
Trích xuất dữ liệu và TỰ ĐỘNG GỢI Ý NHÃN (Pre-labeling).
Tích hợp bộ làm sạch địa chỉ.
"""

import json
import logging
import argparse
import sys
import re
from pathlib import Path
import yaml

# Đảm bảo import từ cùng package
sys.path.insert(0, str(Path(__file__).parent))
from db_connector import DBConnector
from utils.address_cleaner import AddressCleaner
from utils.config_loader import load_config_with_env

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExportAnnotation")

import datetime

import re

class PreLabeler:
    """
    Bộ gán nhãn lai (Hybrid) kết hợp String Matching (Master Data) và Regex (Heuristics).
    Tối ưu cho việc tạo Ground Truth cho mô hình NER PhoBERT.
    """
    
    # Danh sách các thành phố trực thuộc trung ương
    CENTRAL_CITIES = {"hồ chí minh", "hcm", "hà nội", "hn", "đà nẵng", "đn", "hải phòng", "hp", "cần thơ", "ct"}

    # Quy tắc Regex cho các đơn vị vi mô
    MICRO_RULES = [
        ("PCD", r'(?i)(?:\b|^)([23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3})(?:\b|$)', 0.95),
        ("NUM", r'(?i)(?:Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*|(?:\b|^)(?:Lô|Km)\s+[\w\-]+', 0.9),
        ("STR", r'(?i)(?:Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+[^,.\n]+', 0.85),
        ("ALY", r'(?i)(?:Hẻm|Ngõ|Kiệt|Ngách)\s+[^,.\n]+', 0.85),
        ("BLD", r'(?i)(?:Tòa\s*nhà|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|Khu\s*đô\s*thị|KĐT|KCN|CCN|Tầng|Phòng|Lầu|Block)\s+[^,.\n]+', 0.75),
        ("NHB", r'(?i)(?:Khu\s*phố|KP|Tổ\s*dân\s*phố|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC)\s+[^,.\n]+', 0.8),
        ("POI", r'(?i)(?:Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa)\s+[^,.\n]+', 0.7),
    ]

    @classmethod
    def predict(cls, 
                raw_address: str, 
                ward_name: str = None, 
                district_name: str = None, 
                province_name: str = None) -> list:
        
        if not raw_address:
            return []

        results = []
        labeled_spans = [] # Lưu trữ (start, end) để chống quét đè nhãn

        def add_result(start: int, end: int, text: str, label: str, score: float):
            # Kiểm tra chồng lấn
            for s, e in labeled_spans:
                if (s <= start < e) or (s < end <= e):
                    return False
            
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels", "score": score,
                "value": {"start": start, "end": end, "text": text, "labels": [label]}
            })
            labeled_spans.append((start, end))
            return True

        # Giai đoạn 1: String Matching cho các cấp Vĩ mô (Dựa trên Master Data)
        # Sắp xếp theo độ dài giảm dần để ưu tiên khớp cụm từ dài trước
        macros = [
            ("PRO", province_name),
            ("DST", district_name),
            ("WDS", ward_name)
        ]

        for label, entity_name in macros:
            if not entity_name: continue
            
            # Tạo các biến thể tìm kiếm để tăng khả năng khớp
            search_terms = [entity_name]
            # Thêm biến thể bỏ tiền tố (Ví dụ: "Quận 1" -> "1", "Phường Bến Nghé" -> "Bến Nghé")
            short_name = re.sub(r'(?i)^(Thành phố|Tỉnh|Quận|Huyện|Thị xã|Phường|Xã|Thị trấn|TP\.|Q\.|H\.|P\.|X\.)\s*', '', entity_name).strip()
            if short_name and short_name != entity_name:
                search_terms.append(short_name)
            
            for term in sorted(search_terms, key=len, reverse=True):
                # Tìm tất cả các lần xuất hiện (xử lý over-information)
                for match in re.finditer(re.escape(term), raw_address, re.I):
                    add_result(match.start(), match.end(), raw_address[match.start():match.end()], label, 1.0)

        # Giai đoạn 2: Regex Heuristics cho các cấp Vi mô
        for label, pattern, score in cls.MICRO_RULES:
            for match in re.finditer(pattern, raw_address):
                matched_text = match.group(0).strip()
                # Tính toán lại start/end sau khi strip
                start = match.start() + match.group(0).find(matched_text)
                end = start + len(matched_text)
                add_result(start, end, matched_text, label, score)

        return results

from constants import NER_LABELS

def export_label_config(output_file: str):
    """Xuất file XML cấu hình giao diện cho Label Studio."""
    xml_content = '<View>\n  <Labels name="label" toName="text">\n'
    for l in NER_LABELS:
        attrs = f'value="{l["value"]}" background="{l["color"]}"'
        if "alias" in l: attrs += f' alias="{l["alias"]}"'
        if "hint" in l: attrs += f' hint="{l["hint"]}"'
        if "hotkey" in l: attrs += f' hotkey="{l["hotkey"]}"'
        
        xml_content += f'    <Label {attrs}>{l["text"]}</Label>\n'
    
    xml_content += '  </Labels>\n  <Text name="text" value="$text"/>\n</View>'
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_content)
    logger.info(f"📜 Đã xuất cấu hình Label Studio tại {output_file}")

def export_data(config_path: str, output_file: str, limit: int = 5000):
    cfg = load_config_with_env(config_path)
    db_cfg = cfg["database"]
    
    db = DBConnector(db_cfg)
    db.connect()
    
    # Query sử dụng Master Data Join để lấy thông tin chuẩn
    query = f"""
        SELECT 
            acq.id, 
            acq.raw_address,
            w.ward_name,
            d.district_name,
            p.province_name
        FROM prq.address_cleansing_queue acq
        LEFT JOIN mat.ward w ON acq.ward_id = w.ward_id
        LEFT JOIN mat.district d ON acq.district_id = d.district_id
        LEFT JOIN mat.province p ON acq.province_id = p.province_id
        WHERE acq.raw_address IS NOT NULL 
        ORDER BY random() LIMIT {limit}
    """
    
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    db.disconnect()

    annotation_data = []
    for r in rows:
        raw_text = r["raw_address"]
        
        # Gán nhãn Hybrid: Kết hợp Master Data và Heuristics
        predictions = PreLabeler.predict(
            raw_address=raw_text,
            ward_name=r["ward_name"],
            district_name=r["district_name"],
            province_name=r["province_name"]
        )
        
        annotation_data.append({
            "id": int(r["id"]),
            "data": {
                "text": raw_text,
                "meta": {
                    "db_id": r["id"],
                    "context": f"{r['ward_name']}, {r['district_name']}, {r['province_name']}"
                }
            },
            "predictions": [{
                "model_version": "hybrid_v1",
                "result": predictions
            }]
        })

    # Xuất file JSON dữ liệu
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(annotation_data, f, ensure_ascii=False, indent=2)
    
    # Xuất file XML cấu hình (cùng thư mục với file output)
    config_file = str(Path(output_file).with_suffix(".xml")).replace("_prelabeled", "_config")
    export_label_config(config_file)
    
    logger.info(f"✅ Export thành công {len(annotation_data)} mẫu kèm nhãn dự đoán Hybrid.")
    logger.info(f"📁 File dữ liệu: {output_file}")
    logger.info(f"📁 File cấu hình: {config_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="app/ai/config.yaml")
    parser.add_argument("--output", help="Custom output path (optional)")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    # Tạo tên file động: ner_samples_yyyyMMdd_HHmmss_{limit}_prelabeled.json
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not args.output:
        output_path = f"data/ner_samples_{date_str}_{args.limit}_prelabeled.json"
    else:
        output_path = args.output

    export_data(args.config, output_path, args.limit)
