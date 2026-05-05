"""
production_pipeline.py
======================
Hệ thống làm sạch địa chỉ tối ưu (SOTA).
Tích hợp: SQL + NER (PhoBERT) + Abbreviation Map + LLM (Qwen3)
          + ACS Calculator + Epoch Detector.
"""

import logging
import argparse
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime

# Đảm bảo import từ cùng package
sys.path.insert(0, str(Path(__file__).parent))

from db_connector import DBConnector
from models import SiameseMGTE, LLMQwen3, AddressNER
from utils.config_loader import load_config_with_env
from acs_calculator import ACSCalculator
from epoch_detector import EpochDetector

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
    
    # Load corpus từ bảng address_clean_corpus với fallback
    corpus_loaded = False
    try:
        logger.info("Loading corpus from prq.address_clean_corpus...")
        corpus_addresses, corpus_metadata = db.load_clean_corpus_with_metadata(
            admin_epoch="2025",
            source_types=["ADMINISTRATIVE", "QUEUE_STANDARDIZED"],
            min_quality_score=0.7,
            limit=50000  # Giới hạn để tránh memory issues
        )
        
        if len(corpus_addresses) > 0:
            logger.info("Using clean corpus with %d addresses", len(corpus_addresses))
            retriever.encode_corpus_with_metadata(corpus_addresses, corpus_metadata)
            corpus_loaded = True
        else:
            logger.warning("Clean corpus empty, falling back to hierarchical corpus")
            
    except Exception as e:
        logger.warning("Failed to load clean corpus (%s), will try fallback", e)
    
    # Fallback: load hierarchical corpus if needed
    if not corpus_loaded:
        try:
            hierarchical_corpus = db.load_hierarchical_corpus()
            if not hierarchical_corpus or len(hierarchical_corpus) == 0:
                logger.error("Hierarchical corpus is also empty. Pipeline cannot proceed.")
                raise ValueError("No corpus available after trying all sources.")
            logger.info("Using hierarchical corpus with %d addresses", len(hierarchical_corpus))
            retriever.encode_corpus(hierarchical_corpus)
            corpus_loaded = True
        except Exception as e:
            logger.error("Critical: Failed to load any corpus: %s", e)
            raise RuntimeError("Cannot initialize pipeline without corpus data.") from e
    
    if not corpus_loaded:
        logger.error("Critical: Corpus was not loaded successfully")
        raise RuntimeError("Pipeline initialization failed: corpus not loaded.")
    
    # Load NER Model (Đã Fine-tuned hoặc dùng Regex fallback)
    ner_path = "models/phobert-ner-vn"
    ner_model_path = ner_path if Path(ner_path).exists() else ""
    if not ner_model_path:
        logger.info("Fine-tuned NER model not found at models/phobert-ner-vn. Regex fallback will be used.")
    ner = AddressNER(model_path=ner_model_path)
    
    llm = LLMQwen3(model_name=mod_cfg["llm"]["model_name"], use_quantization=False)

    # ACS Calculator và Epoch Detector (không cần DB session ở pipeline standalone)
    acs_calc     = ACSCalculator(db_session=None)
    epoch_detector = EpochDetector(db_session=None)

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

    logger.info(f"Processing {len(rows):,} rows with Hybrid Pipeline...")

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

            standardized = llm_data.get("full_address") or context_addr

            # E. Epoch Detection
            epoch_result = epoch_detector.detect(raw_addr)

            # F. ACS Calculation
            acs = acs_calc.compute(
                raw_address=raw_addr,
                standardized_address=standardized,
                semantic_score=float(llm_score),
                province_id=row.get("province_id"),
                district_id=row.get("district_id"),
                ward_id=row.get("ward_id"),
                admin_version=2,  # Default Post-2025; epoch detector cập nhật
            )

            batch_results.append({
                "id": row['id'],
                "processing_status": "DONE",
                "processing_method": "HYBRID_V1",
                "address_standardized": standardized,
                "phobert_confidence_score": float(llm_score),
                "phobert_parsed_components": json.dumps(ner_results),
                "acs_score": float(acs.acs_score),
                "acs_decision": acs.acs_decision,
                "s_text": float(acs.s_text),
                "s_sem": float(acs.s_sem),
                "v_hierarchy": float(acs.v_hierarchy),
                "v_temporal": float(acs.v_temporal),
                "address_epoch": epoch_result.epoch,
            })
            
            if len(batch_results) % 50 == 0:
                logger.info(f" Progress: {len(batch_results):,}/{len(rows):,}")
                
        except IndexError as e:
            row_id = row.get("id")
            row_id_display = f"{row_id:,}" if isinstance(row_id, int) else str(row_id)
            error_context = traceback.format_exc()
            logger.error(
                f"IndexError processing row {row_id_display}: {e}\n"
                f"This may indicate corrupt embeddings or invalid corpus state.\n"
                f"Stack trace:\n{error_context}"
            )
            batch_results.append({
                "id": row['id'],
                "processing_status": "ERROR",
                "error_message": f"IndexError: {str(e)}"
            })
            
        except Exception as e:
            row_id = row.get("id")
            row_id_display = f"{row_id:,}" if isinstance(row_id, int) else str(row_id)
            error_context = traceback.format_exc()
            logger.error(
                f"Error processing row {row_id_display}: {e}\n"
                f"Type: {type(e).__name__}\n"
                f"Stack trace:\n{error_context}"
            )
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
            "phobert_confidence_score", "phobert_parsed_components", "error_message",
            "acs_score", "acs_decision", "s_text", "s_sem",
            "v_hierarchy", "v_temporal", "address_epoch",
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
