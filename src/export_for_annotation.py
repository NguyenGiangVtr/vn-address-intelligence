"""
export_for_annotation.py
========================
Trích xuất dữ liệu từ PostgreSQL để phục vụ gán nhãn NER (Labeling).
Định dạng đầu ra: JSON (Tương thích Label Studio).
"""

import json
import logging
import argparse
import sys
from pathlib import Path
import yaml

# Đảm bảo import từ cùng package
sys.path.insert(0, str(Path(__file__).parent))
from db_connector import DBConnector

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExportAnnotation")

def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def export_data(config_path: str, output_file: str, limit: int = 5000):
    cfg = _load_config(config_path)
    db_cfg = cfg["database"]
    
    db = DBConnector(db_cfg)
    db.connect()
    
    # Query lấy mẫu ngẫu nhiên để đảm bảo tính đa dạng của địa chỉ
    query = f"""
        SELECT 
            id, 
            street_address, 
            ward_name, 
            district_name, 
            province_name,
            address_raw
        FROM {db_cfg['schema']}.{db_cfg['table_name']}
        WHERE street_address IS NOT NULL 
          AND NULLIF(TRIM(street_address), '') IS NOT NULL
        ORDER BY random()
        LIMIT {limit}
    """
    
    logger.info(f"📥 Đang truy vấn {limit} mẫu dữ liệu từ DB...")
    
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    db.disconnect()
    
    if not rows:
        logger.warning("❌ Không tìm thấy dữ liệu phù hợp để export.")
        return

    # Chuyển đổi sang định dạng Label Studio (List of dicts)
    annotation_data = []
    for r in rows:
        # Chúng ta gộp context vào metadata để người gán nhãn có thêm thông tin tham khảo
        annotation_data.append({
            "data": {
                "text": r["street_address"],
                "meta": {
                    "db_id": r["id"],
                    "context": f"{r['ward_name']}, {r['district_name']}, {r['province_name']}",
                    "raw": r["address_raw"]
                }
            }
        })

    # Lưu ra file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotation_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Đã export {len(annotation_data)} mẫu vào: {output_path}")
    logger.info("💡 Hướng dẫn: Mở Label Studio -> Import file này -> Chọn template 'Named Entity Recognition'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export data for NER labeling")
    parser.add_argument("--config", default="src/config.yaml", help="Path to config.yaml")
    parser.add_argument("--output", default="data/ner_samples.json", help="File đầu ra")
    parser.add_argument("--limit", type=int, default=5000, help="Số lượng mẫu")
    args = parser.parse_args()
    
    export_data(args.config, args.output, args.limit)
