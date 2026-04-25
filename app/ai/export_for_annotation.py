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

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExportAnnotation")

class PreLabeler:
    """Bộ dự đoán nhãn dựa trên quy tắc (Heuristics) để hỗ trợ gán nhãn nhanh."""
    
    @staticmethod
    def predict(text: str) -> list:
        results = []
        
        # 1. Dự đoán Số nhà (NUM) - Thường ở đầu chuỗi
        num_match = re.search(r'^(Số\s)?([\d\w/.\-]+)', text, re.I)
        if num_match:
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels",
                "value": {
                    "start": num_match.start(2),
                    "end": num_match.end(2),
                    "text": num_match.group(2),
                    "labels": ["NUM"]
                }
            })

        # 2. Dự đoán Tên đường (STR) - Sau số nhà hoặc có từ khóa "Đường"
        street_match = re.search(r'(Đường|Phố|QL|ĐT|Tỉnh lộ)\s+([^,]+)', text, re.I)
        if street_match:
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels",
                "value": {
                    "start": street_match.start(0),
                    "end": street_match.end(0),
                    "text": street_match.group(0),
                    "labels": ["STR"]
                }
            })
            
        # 3. Dự đoán Hẻm/Ngõ (ALY)
        aly_match = re.search(r'(Hẻm|Ngõ|Kiệt|Ngách)\s+([\d/]+)', text, re.I)
        if aly_match:
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels",
                "value": {
                    "start": aly_match.start(0),
                    "end": aly_match.end(0),
                    "text": aly_match.group(0),
                    "labels": ["ALY"]
                }
            })

        return results

def export_data(config_path: str, output_file: str, limit: int = 5000):
    cfg = _load_config(config_path)
    db_cfg = cfg["database"]
    
    db = DBConnector(db_cfg)
    db.connect()
    cleaner = AddressCleaner()
    
    query = f"""
        SELECT id, street_address, ward_name, district_name, province_name, address_raw
        FROM scm.address
        WHERE street_address IS NOT NULL 
        ORDER BY random() LIMIT {limit}
    """
    
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    db.disconnect()

    annotation_data = []
    for r in rows:
        # Tiền xử lý làm sạch dữ liệu (Giai đoạn 1)
        cleaned_text = cleaner.pre_process_for_labeling(r["street_address"])
        
        # Dự đoán nhãn nháp (Giai đoạn 2)
        predictions = PreLabeler.predict(cleaned_text)
        
        annotation_data.append({
            "data": {
                "text": cleaned_text,
                "meta": {
                    "db_id": r["id"],
                    "context": f"{r['ward_name']}, {r['district_name']}, {r['province_name']}",
                    "raw": r["address_raw"]
                }
            },
            "predictions": [{
                "model_version": "heuristic_v1",
                "result": predictions
            }]
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(annotation_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Export thành công {len(annotation_data)} mẫu kèm nhãn dự đoán nháp.")

def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="src/config.yaml")
    parser.add_argument("--output", default="data/ner_samples_prelabeled.json")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    export_data(args.config, args.output, args.limit)
