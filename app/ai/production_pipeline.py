"""
production_pipeline.py
======================
Hệ thống làm sạch địa chỉ tối ưu (SOTA).
Tích hợp: SQL + NER (PhoBERT) + Abbreviation Map + LLM (Qwen3).
"""

import logging
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Đảm bảo import từ cùng package
sys.path.insert(0, str(Path(__file__).parent))

from db_connector import DBConnector
from models import SiameseMGTE, LLMQwen3, AddressNER
from utils.config_loader import load_config_with_env

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ProductionPipeline")

def run_pipeline(config_path: str, limit: int = None):
    cfg = load_config_with_env(config_path)
    db_cfg = cfg["database"]
    mod_cfg = cfg["models"]
    
    # Load Abbreviation Map
    abbr_map_path = Path("assets/abbreviation_map.json")
    if abbr_map_path.exists():
        with open(abbr_map_path, encoding="utf-8") as f:
            abbr_map = json.load(f)
    else:
        abbr_map = {'STREET_PREFIX': {}}
    
    db = DBConnector(db_cfg)
    db.connect()
    
    # 1. Khởi tạo các mô hình ──────────────────────────────────────────────────
    logger.info("Initializing models...")
    retriever = SiameseMGTE(model_name=mod_cfg["siamese_mgte"]["model_name"])
    retriever.encode_corpus(db.load_hierarchical_corpus())
    
    # Load NER Model (Đã Fine-tuned hoặc dùng Regex fallback)
    ner_path = "models/phobert-ner-vn"
    ner = AddressNER(model_path=ner_path if Path(ner_path).exists() else "vinai/phobert-base")
    
    llm = LLMQwen3(model_name=mod_cfg["llm"]["model_name"], use_quantization=False)

    # 2. Xử lý Dữ liệu ─────────────────────────────────────────────────────────
    # Lấy những bản ghi đang PENDING hoặc chưa có address_standardized
    query = f"""
        SELECT id, raw_address, street_address, ward_name, district_name, province_name 
        FROM prq.address_cleansing_queue
        WHERE processing_status = 'PENDING' OR address_standardized IS NULL
    """
    if limit: 
        query += f" LIMIT {limit}"
        
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    if not rows:
        logger.info("No records found to process.")
        db.disconnect()
        return

    logger.info(f"Processing {len(rows)} rows with Hybrid Pipeline...")

    batch_results = []
    for row in rows:
        try:
            raw_addr = row.get('raw_address') or row.get('street_address')
            if not raw_addr:
                continue
                
            # A. NER bóc tách street_address
            ner_results = ner.extract(raw_addr)
            
            # B. Chuẩn hóa sơ bộ bằng Dictionary
            street_name = ner_results.get('STR', raw_addr)
            for k, v in abbr_map.get('STREET_PREFIX', {}).items():
                if street_name.lower().startswith(k.lower()):
                    street_name = v + street_name[len(k):]
            
            # C. Tổng hợp context cho LLM
            nhb_part = ner_results.get('NHB', '')
            num_part = ner_results.get('NUM', '')
            
            context_parts = []
            if num_part: context_parts.append(num_part)
            if street_name: context_parts.append(street_name)
            if nhb_part: context_parts.append(nhb_part)
            if row.get('ward_name'): context_parts.append(row['ward_name'])
            if row.get('district_name'): context_parts.append(row['district_name'])
            if row.get('province_name'): context_parts.append(row['province_name'])
            
            context_addr = ", ".join([p for p in context_parts if p])
            
            # D. LLM Final Normalization
            llm_data, llm_score, _ = llm.normalize(context_addr, []) 
            
            if not isinstance(llm_data, dict):
                llm_data = {"full_address": str(llm_data)}

            batch_results.append({
                "id": row['id'],
                "processing_status": "DONE",
                "processing_method": "HYBRID_V1",
                "address_standardized": llm_data.get("full_address"),
                "phobert_confidence_score": float(llm_score),
                "phobert_parsed_components": json.dumps(ner_results)
            })
            
            if len(batch_results) % 50 == 0:
                logger.info(f" Progress: {len(batch_results)}/{len(rows)}")
                
        except Exception as e:
            logger.error(f"Error processing row {row.get('id')}: {e}")
            batch_results.append({
                "id": row['id'],
                "processing_status": "ERROR",
                "error_message": str(e)
            })

    # 3. Lưu kết quả ────────────────────────────────────────────────────────────
    if batch_results:
        ids = [r["id"] for r in batch_results]
        
        # Cập nhật từng cột
        cols_to_update = [
            "processing_status", "processing_method", "address_standardized", 
            "phobert_confidence_score", "phobert_parsed_components", "error_message"
        ]
        
        for col in cols_to_update:
            vals = [r.get(col) for r in batch_results]
            # Chỉ update nếu có dữ liệu (tránh overwrite bằng None nếu không muốn)
            if any(v is not None for v in vals):
                db.save_results(db_cfg["table_name"], col, ids, vals)

    db.disconnect()
    logger.info("Pipeline hoàn tất.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="app/ai/config.yaml")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run_pipeline(args.config, args.limit)
