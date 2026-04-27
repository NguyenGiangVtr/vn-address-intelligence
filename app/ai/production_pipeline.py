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
import numpy as np
import yaml

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
    with open("assets/abbreviation_map.json", encoding="utf-8") as f:
        abbr_map = json.load(f)
    
    db = DBConnector(db_cfg)
    db.connect()
    
    # 1. Khởi tạo các mô hình ──────────────────────────────────────────────────
    retriever = SiameseMGTE(model_name=mod_cfg["siamese_mgte"]["model_name"])
    retriever.encode_corpus(db.load_hierarchical_corpus())
    
    # Load NER Model (Đã Fine-tuned hoặc dùng Regex fallback)
    ner = AddressNER(model_path="models/phobert-ner-vn" if Path("models/phobert-ner-vn").exists() else "vinai/phobert-base")
    
    llm = LLMQwen3(model_name=mod_cfg["llm"]["model_name"], use_quantization=False)

    # 2. Xử lý Dữ liệu ─────────────────────────────────────────────────────────
    query = f"""
        SELECT id, street_address, ward_name, district_name, province_name 
        FROM prq.address_cleansing_queue
        WHERE street_address IS NOT NULL AND address_standardized IS NULL
    """
    if limit: query += f" LIMIT {limit}"
        
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    if not rows: return

    logger.info(f"🚀 Processing {len(rows)} rows with Hybrid Pipeline...")

    batch_results = []
    for row in rows:
        # A. NER bóc tách street_address
        ner_results = ner.extract(row['street_address'])
        
        # B. Chuẩn hóa sơ bộ bằng Dictionary
        street_name = ner_results.get('STR', row['street_address'])
        for k, v in abbr_map['STREET_PREFIX'].items():
            if street_name.lower().startswith(k):
                street_name = street_name.replace(street_name[:len(k)], v)
        
        # C. Tổng hợp context cho LLM
        # Bổ sung NHB (Khu phố/Thôn/Ấp) nếu bóc tách được
        nhb_part = ner_results.get('NHB', '')
        context_addr = f"{ner_results.get('NUM', '')} {street_name}, {nhb_part + ', ' if nhb_part else ''}{row['ward_name']}, {row['district_name']}, {row['province_name']}"
        
        # D. LLM Final Normalization
        llm_data, llm_score, _ = llm.normalize(context_addr, []) # Candidates có thể lấy từ retriever nếu cần
        
        if not isinstance(llm_data, dict):
            llm_data = {"full_address": str(llm_data)}

        batch_results.append({
            "id": row['id'],
            "is_standardized": True,
            "confidence_score": float(llm_score),
            "processing_method": "HYBRID_NER_LLM",
            "address_standardized": llm_data.get("full_address")
        })

    # 3. Lưu kết quả ────────────────────────────────────────────────────────────
    ids = [r["id"] for r in batch_results]
    db.save_results(db_cfg["table_name"], "is_standardized", ids, [r["is_standardized"] for r in batch_results])
    db.save_results(db_cfg["table_name"], "confidence_score", ids, [r["confidence_score"] for r in batch_results])
    db.save_results(db_cfg["table_name"], "processing_method", ids, [r["processing_method"] for r in batch_results])
    db.save_results(db_cfg["table_name"], "address_standardized", ids, [r["address_standardized"] for r in batch_results])

    db.disconnect()
    logger.info("✅ Pipeline hoàn tất.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="app/ai/config.yaml")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run_pipeline(args.config, args.limit)
