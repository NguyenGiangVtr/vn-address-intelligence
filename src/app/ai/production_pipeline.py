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
from models import SiameseMGTE, LLMQwen3, AddressNER, DEFAULT_HF_NER_MODEL_ID, resolve_ner_model_path
from utils.config_loader import load_config_with_env
from acs_calculator import ACSCalculator
from epoch_detector import EpochDetector

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ProductionPipeline")

def run_pipeline(config_path: str, limit: int = None, 
                 use_ner: bool = True, 
                 use_retrieval: bool = True, 
                 use_llm: bool = True,
                 retriever_type: str = "mgte",
                 supa_run_id: int = None):
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

    exp_cfg = cfg.get("experiment") or {}
    corpus_limit = int(exp_cfg.get("corpus_limit", 50000) or 50000)
    if corpus_limit < 1:
        corpus_limit = 50000
    
    # 1. Khởi tạo các mô hình ──────────────────────────────────────────────────
    logger.info("Initializing models (NER=%s, Retrieval=%s [%s], LLM=%s)...", 
                use_ner, use_retrieval, retriever_type, use_llm)
    
    retriever = None
    if use_retrieval:
        if retriever_type == "phobert":
            from models import PhoBERTSiamese
            retriever = PhoBERTSiamese(model_name=mod_cfg.get("phobert_siamese", {}).get("model_name", "vinai/phobert-base"))
        else:
            retriever = SiameseMGTE(model_name=mod_cfg["siamese_mgte"]["model_name"])
        
        # Load corpus
        corpus_loaded = False
        try:
            logger.info("Loading corpus for %s (limit=%s)...", retriever_type, corpus_limit)
            corpus_addresses, corpus_metadata = db.load_clean_corpus_with_metadata(
                admin_epoch="2025",
                source_types=["ADMINISTRATIVE", "QUEUE_STANDARDIZED", "HF_NER_DERIVED"],
                min_quality_score=0.7,
                limit=corpus_limit,
            )
            
            if len(corpus_addresses) > 0:
                logger.info("Using clean corpus with %d addresses", len(corpus_addresses))
                retriever.encode_corpus_with_metadata(corpus_addresses, corpus_metadata)
                corpus_loaded = True
            else:
                logger.warning("Clean corpus empty, falling back to hierarchical corpus")
        except Exception as e:
            logger.warning("Failed to load clean corpus (%s), will try fallback", e)
        
        if not corpus_loaded:
            hierarchical_corpus = db.load_hierarchical_corpus()
            if hierarchical_corpus:
                retriever.encode_corpus(hierarchical_corpus)
            else:
                logger.error("No corpus available for retrieval. Disabling retrieval.")
                use_retrieval = False

    ner = None
    if use_ner:
        ner_model_path = resolve_ner_model_path()
        ner = AddressNER(model_path=ner_model_path)
    
    llm = None
    if use_llm:
        llm = LLMQwen3(
            model_name=mod_cfg["llm"]["model_name"],
            use_quantization=bool(mod_cfg["llm"].get("use_quantization", True)),
            quantization_bits=int(mod_cfg["llm"].get("quantization_bits", 8)),
            max_new_tokens=int(mod_cfg["llm"].get("max_new_tokens", 128)),
            temperature=float(mod_cfg["llm"].get("temperature", 0.0)),
        )

    acs_calc = ACSCalculator(db_session=None)
    epoch_detector = EpochDetector(db_session=None)

    # 2. Xử lý Dữ liệu ─────────────────────────────────────────────────────────
    if supa_run_id:
        logger.info(f"Targeting SUPA Specimens for run_id={supa_run_id}")
        query = f"""
            SELECT id, noisy_raw_address as raw_address, 
                   ward_id, district_id, province_id,
                   latitude, longitude
            FROM prq.supa_benchmark_specimen
            WHERE run_id = {supa_run_id}
        """
        table_to_save = "supa_benchmark_specimen"
    else:
        query = f"""
            SELECT id, raw_address, street_address, ward_name, district_name, province_name,
                   ward_id, district_id, province_id,
                   latitude, longitude
            FROM prq.address_cleansing_queue
            WHERE processing_status = 'PENDING' OR address_standardized IS NULL
        """
        table_to_save = db_cfg["table_name"]

    if limit: 
        query += f" LIMIT {limit}"
        
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    if not rows:
        logger.info("No records found to process.")
        db.disconnect()
        return

    # Xác định tag phương pháp dựa trên cấu hình
    method_parts = ["HYBRID"]
    if use_ner: method_parts.append("NER")
    if use_retrieval: method_parts.append(retriever_type.upper())
    if use_llm: method_parts.append("LLM")
    method_tag = "_".join(method_parts)

    logger.info(f"Processing {len(rows):,} rows with {method_tag}...")

    batch_results = []
    for row in rows:
        start_time = datetime.now()
        try:
            raw_addr = row.get('raw_address') or row.get('street_address')
            if not raw_addr: continue
                
            # A. NER
            ner_results = {}
            if use_ner:
                ner_results = ner.extract(raw_addr)
            
            # B. Dictionary Normalization (Street name)
            street_name = ner_results.get('STR', raw_addr)
            for k, v in abbr_map.get('STREET_PREFIX', {}).items():
                if street_name.lower().startswith(k.lower()):
                    street_name = v + street_name[len(k):]
            
            # C. Context Assembly
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
            
            # D. Retrieval
            ranked = []
            top_meta = {}
            top_score = 0.0
            if use_retrieval:
                ranked = retriever.retrieve_top_k_with_meta(context_addr, top_k=5)
                if ranked:
                    top_score = float(ranked[0][1])
                    top_meta = ranked[0][2]
            
            # E. LLM
            llm_score = 0.0
            if use_llm:
                top_candidates = [c for c, _, _ in ranked] if use_retrieval else []
                llm_data, llm_score, _ = llm.normalize(context_addr, top_candidates)
                if not isinstance(llm_data, dict):
                    llm_data = {"full_address": str(llm_data)}
                standardized = llm_data.get("full_address") or context_addr
            else:
                # Fallback if no LLM: Use top candidate from retrieval or context_addr
                if use_retrieval and ranked:
                    standardized = ranked[0][0]
                else:
                    standardized = context_addr

            # F. Decision & ACS
            epoch_result = epoch_detector.detect(raw_addr)
            semantic_score = max(float(llm_score), top_score)

            row_lat = row.get("latitude")
            row_lon = row.get("longitude")
            backfill_lat = top_meta.get("latitude") if row_lat is None else None
            backfill_lon = top_meta.get("longitude") if row_lon is None else None

            acs = acs_calc.compute(
                raw_address=raw_addr,
                standardized_address=standardized,
                semantic_score=semantic_score,
                province_id=row.get("province_id"),
                district_id=row.get("district_id"),
                ward_id=row.get("ward_id"),
                admin_version=2,
                latitude=row_lat if row_lat is not None else backfill_lat,
                longitude=row_lon if row_lon is not None else backfill_lon,
            )

            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result_payload = {
                "id": row['id'],
                "processing_status": "DONE",
                "processing_method": method_tag,
                "address_standardized": standardized,
                "phobert_confidence_score": float(llm_score),
                "phobert_parsed_components": json.dumps(ner_results),
                "mgte_confidence_score": top_score,
                "acs_score": float(acs.acs_score),
                "acs_decision": acs.acs_decision,
                "address_epoch": epoch_result.epoch,
                "latency_ms": latency_ms
            }
            if supa_run_id:
                # Map standardized to pred_standardized for SUPA table
                result_payload["pred_standardized"] = standardized

            if backfill_lat is not None: result_payload["latitude"] = backfill_lat
            if backfill_lon is not None: result_payload["longitude"] = backfill_lon
            batch_results.append(result_payload)
            
            if len(batch_results) % 50 == 0:
                logger.info(f" Progress: {len(batch_results):,}/{len(rows):,}")
                
        except Exception as e:
            logger.error(f"Error row {row.get('id')}: {e}")
            batch_results.append({"id": row['id'], "processing_status": "ERROR", "error_message": str(e)})

    # 3. Lưu kết quả
    if batch_results:
        ids = [r["id"] for r in batch_results]
        if supa_run_id:
            # SUPA Mode: only update relevant evaluation columns
            cols_to_update = ["pred_standardized", "latency_ms"]
        else:
            cols_to_update = [
                "processing_status", "processing_method", "address_standardized",
                "phobert_confidence_score", "phobert_parsed_components",
                "mgte_confidence_score", "latitude", "longitude", "error_message",
                "acs_score", "acs_decision", "address_epoch"
            ]
            
        for col in cols_to_update:
            vals = [r.get(col) for r in batch_results]
            if any(v is not None for v in vals):
                db.save_results(table_to_save, col, ids, vals)

    db.disconnect()
    logger.info("Pipeline hoàn tất.")

if __name__ == "__main__":
    from app.paths import ai_config_yaml_relative_posix

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=ai_config_yaml_relative_posix())
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-ner", action="store_true", help="Skip AddressNER component")
    parser.add_argument("--no-retrieval", action="store_true", help="Skip Siamese Retrieval component")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM Normalization component")
    parser.add_argument("--retriever-type", choices=["mgte", "phobert"], default="mgte", help="Backbone for retrieval")
    parser.add_argument("--supa-run-id", type=int, help="Target a specific SUPA benchmark run")
    
    args = parser.parse_args()
    run_pipeline(
        args.config, 
        args.limit,
        use_ner=not args.no_ner,
        use_retrieval=not args.no_retrieval,
        use_llm=not args.no_llm,
        retriever_type=args.retriever_type,
        supa_run_id=args.supa_run_id
    )
