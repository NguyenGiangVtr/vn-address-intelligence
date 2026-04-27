"""
experiment_runner.py
====================
Entry-point chính: đọc config → load data từ PostgreSQL → chạy 3 mô hình
→ đo metrics → ghi kết quả vào DB → sinh báo cáo HTML + CSV.

Cách chạy:
    python src/experiment_runner.py --config src/config.yaml
    python src/experiment_runner.py --config src/config.yaml --no-llm
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# Đảm bảo import từ cùng package
sys.path.insert(0, str(Path(__file__).parent))

from db_connector import DBConnector
from metrics import compute_metrics, print_metrics
from models import LLMQwen3, PhoBERTSiamese, SiameseMGTE
from report_generator import generate_html_report, save_csv
from utils.config_loader import load_config_with_env

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ExperimentRunner")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _load_config(path: str) -> dict:
    return load_config_with_env(path)


def _has_ground_truth(df: pd.DataFrame) -> bool:
    return "standard_address" in df.columns and df["standard_address"].notna().any()


# ──────────────────────────────────────────────────────────────────────────────
# Run một model và trả về (results_list, latencies_list)
# ──────────────────────────────────────────────────────────────────────────────
def _run_phobert(queries, corpus, cfg) -> tuple:
    model = PhoBERTSiamese(
        model_name=cfg["model_name"],
        max_seq_length=cfg.get("max_seq_length", 256),
        batch_size=cfg.get("batch_size", 32),
        device=cfg.get("device", "auto"),
    )
    model.encode_corpus(corpus)
    results, latencies = [], []
    for q in queries:
        addr, _, lat = model.normalize(q)
        results.append(addr)
        latencies.append(lat)
    del model
    return results, latencies


def _run_mgte(queries, corpus, cfg) -> tuple:
    model = SiameseMGTE(
        model_name=cfg["model_name"],
        batch_size=cfg.get("batch_size", 32),
        device=cfg.get("device", "auto"),
    )
    model.encode_corpus(corpus)
    results, latencies = [], []
    for q in queries:
        addr, _, lat = model.normalize(q)
        results.append(addr)
        latencies.append(lat)
    del model
    return results, latencies


def _run_llm(queries, corpus, cfg, mgte_results) -> tuple:
    """
    LLM dùng kết quả top-5 từ mGTE retriever làm candidates
    để tăng chất lượng và giảm hallucination.
    """
    # Tạo candidates nhanh bằng mGTE
    retriever = SiameseMGTE(
        model_name="Alibaba-NLP/gte-multilingual-base",
        batch_size=cfg.get("batch_size", 32),
        device=cfg.get("device", "auto"),
    )
    retriever.encode_corpus(corpus)

    import numpy as np
    retriever_emb = retriever._corpus_emb

    llm = LLMQwen3(
        model_name=cfg["model_name"],
        use_quantization=cfg.get("use_quantization", True),
        max_new_tokens=cfg.get("max_new_tokens", 256),
        temperature=cfg.get("temperature", 0.3),
        device=cfg.get("device", "auto"),
    )

    results, latencies = [], []
    for q in queries:
        q_emb    = retriever.model.encode([q], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores   = retriever_emb @ q_emb
        top5_idx = np.argsort(scores)[::-1][:5]
        cands    = [corpus[i] for i in top5_idx]
        addr, _, lat = llm.normalize(q, cands)
        results.append(addr)
        latencies.append(lat)

    del retriever, llm
    return results, latencies


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main(config_path: str, skip_llm: bool = False):
    cfg = _load_config(config_path)

    db_cfg   = cfg["database"]
    exp_cfg  = cfg["experiment"]
    mod_cfg  = cfg["models"]
    batch_sz = db_cfg.get("db_batch_size", 100)

    # 1. Kết nối DB ──────────────────────────────────────────────────────────
    db = DBConnector(db_cfg)
    db.connect()

    # 2. Load dữ liệu ────────────────────────────────────────────────────────
    df = db.load_addresses(
        table=db_cfg["table_name"],
        input_col=db_cfg["input_column"],
        gt_col=db_cfg.get("ground_truth_column", ""),
        limit=db_cfg.get("limit"),
    )
    has_gt  = _has_ground_truth(df)
    queries = df["raw_address"].fillna("").tolist()

    corpus = db.load_standard_addresses(
        table=exp_cfg["standard_addresses_table"],
        col=exp_cfg["standard_addresses_column"],
        schema=exp_cfg.get("standard_addresses_schema", ""),
        limit=exp_cfg.get("corpus_limit"),
    )

    logger.info("Queries: %d | Corpus: %d | Ground-truth: %s",
                len(queries), len(corpus), has_gt)

    all_metrics: dict = {}
    detail_data: dict = {"id": df["id"].tolist(), "raw_address": queries}
    if has_gt:
        detail_data["standard_address"] = df["standard_address"].tolist()

    # 3. PhoBERT ─────────────────────────────────────────────────────────────
    if mod_cfg["phobert"]["enabled"]:
        logger.info("=" * 60)
        logger.info("▶  Chạy PhoBERT Siamese ...")
        pb_results, pb_lats = _run_phobert(queries, corpus, mod_cfg["phobert"])
        col_pb = mod_cfg["phobert"]["result_column"]
        detail_data[col_pb] = pb_results

        db.save_results(db_cfg["table_name"], col_pb, df["id"].tolist(), pb_results, batch_size=batch_sz)

        if has_gt:
            gts = df["standard_address"].tolist()
            all_metrics["PhoBERT"] = compute_metrics(pb_results, gts, pb_lats)
            print_metrics("PhoBERT", all_metrics["PhoBERT"])

    # 4. mGTE ────────────────────────────────────────────────────────────────
    if mod_cfg["siamese_mgte"]["enabled"]:
        logger.info("=" * 60)
        logger.info("▶  Chạy mGTE Siamese ...")
        mg_results, mg_lats = _run_mgte(queries, corpus, mod_cfg["siamese_mgte"])
        col_mg = mod_cfg["siamese_mgte"]["result_column"]
        detail_data[col_mg] = mg_results

        db.save_results(db_cfg["table_name"], col_mg, df["id"].tolist(), mg_results, batch_size=batch_sz)

        if has_gt:
            gts = df["standard_address"].tolist()
            all_metrics["mGTE"] = compute_metrics(mg_results, gts, mg_lats)
            print_metrics("mGTE", all_metrics["mGTE"])
    else:
        mg_results = []

    # 5. LLM ─────────────────────────────────────────────────────────────────
    if mod_cfg["llm"]["enabled"] and not skip_llm:
        logger.info("=" * 60)
        logger.info("▶  Chạy LLM (Qwen3) ...")
        llm_results, llm_lats = _run_llm(
            queries, corpus, mod_cfg["llm"], mg_results
        )
        col_llm = mod_cfg["llm"]["result_column"]
        detail_data[col_llm] = llm_results

        db.save_results(db_cfg["table_name"], col_llm, df["id"].tolist(), llm_results, batch_size=batch_sz)

        if has_gt:
            gts = df["standard_address"].tolist()
            all_metrics["LLM"] = compute_metrics(llm_results, gts, llm_lats)
            print_metrics("LLM", all_metrics["LLM"])

    db.disconnect()

    # 6. Báo cáo ─────────────────────────────────────────────────────────────
    detail_df = pd.DataFrame(detail_data)

    if exp_cfg.get("save_csv"):
        save_csv(detail_df, exp_cfg["csv_path"])

    if all_metrics:
        generate_html_report(
            all_metrics=all_metrics,
            detail_df=detail_df,
            output_path=exp_cfg["output_report_path"],
        )
    else:
        logger.warning(
            "Không có ground-truth → bỏ qua tính metrics. "
            "Kết quả chuẩn hóa đã lưu vào DB và CSV."
        )

    logger.info("✅ Thực nghiệm hoàn tất!")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Thực nghiệm so sánh PhoBERT / mGTE / LLM"
    )
    parser.add_argument(
        "--config", default="app/ai/config.yaml", help="Đường dẫn file config YAML"
    )
    parser.add_argument(
        "--no-llm", action="store_true", help="Bỏ qua LLM (nhanh hơn)"
    )
    args = parser.parse_args()
    main(config_path=args.config, skip_llm=args.no_llm)
