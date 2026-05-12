"""
train_ner.py
============
Script huấn luyện mô hình NER PhoBERT với dữ liệu từ Label Studio.
Sử dụng HuggingFace Trainer API + seqeval để đánh giá.

Cách chạy:
    python app/ai/train_ner.py --data data/labeled_export.json
    python app/ai/train_ner.py --data data/labeled_export.json --epochs 20 --lr 3e-5
    python app/ai/train_ner.py --hf-dataset dathuynh1108/ner-address-standard-dataset --hf-max-train 20000
"""

import sys
from pathlib import Path

for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
import _bootstrap_import_paths  # noqa: E402

_bootstrap_import_paths.install()

import os
import json
import logging
import argparse
import re
from itertools import islice
from typing import Optional

import torch
import numpy as np
import inspect
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback
)
from seqeval.metrics import classification_report, f1_score, precision_score, recall_score

from app.ai.constants import get_ner_label_list, NER_LABELS
from app.ai.job_artifacts import record_training_history
from app.core.database import SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("TrainNER")

# BIO từ https://huggingface.co/datasets/dathuynh1108/ner-address-standard-dataset → nhãn dự án (constants)
HF_STANDARD_BIO_TO_PROJECT = {
    "O": "O",
    "B-STREET": "B-STR",
    "I-STREET": "I-STR",
    "B-WARD": "B-WDS",
    "I-WARD": "I-WDS",
    "B-DISTRICT": "B-DST",
    "I-DISTRICT": "I-DST",
    "B-PROVINCE": "B-PRO",
    "I-PROVINCE": "I-PRO",
    "B-FLOOR": "B-ALY",
    "I-FLOOR": "I-ALY",
    "B-ROOM": "B-PCD",
    "I-ROOM": "I-PCD",
}

# Fallback ID mapping for the HF standard dataset when ClassLabel metadata is unavailable.
HF_STANDARD_ID_TO_BIO = {
    0: "O",
    1: "B-STREET",
    2: "I-STREET",
    3: "B-WARD",
    4: "I-WARD",
    5: "B-DISTRICT",
    6: "I-DISTRICT",
    7: "B-PROVINCE",
    8: "I-PROVINCE",
    9: "B-FLOOR",
    10: "I-FLOOR",
    11: "B-ROOM",
    12: "I-ROOM",
}

REQUIRED_ENTITY_LABELS = {"NUM", "STR", "WDS", "DST", "PRO", "NHB", "BLD", "POI", "ALY", "PCD"}

# ──────────────────────────────────────────────────────────────────────────────
# Bước 1: Chuyển đổi Label Studio JSON → BIO Tokens
# ──────────────────────────────────────────────────────────────────────────────

def convert_labelstudio_to_bio(data: list, tokenizer, label2id: dict) -> list:
    """
    Chuyển đổi dữ liệu export từ Label Studio sang định dạng BIO cho PhoBERT.

    Input: List các items từ Label Studio JSON export
    Output: List các dict với keys: [input_ids, attention_mask, labels]

    Logic xử lý (tương thích PhoBERT slow tokenizer - không có offset_mapping):
    1. Tách text thành các từ bằng khoảng trắng
    2. Tokenize từng từ riêng biệt để biết mỗi từ tạo ra bao nhiêu sub-tokens
    3. Gán nhãn BIO dựa trên vị trí ký tự (character offset) của từng từ
    4. Sub-tokens (không phải đầu từ) → -100 (ignored by loss)
    5. Special tokens (<s>, </s>) → -100
    """
    processed = []
    skipped = 0

    for item in data:
        text = item.get("data", {}).get("text", "")
        if not text:
            skipped += 1
            continue

        # Lấy annotations (ưu tiên annotations > predictions)
        annotations = []
        if "annotations" in item and item["annotations"]:
            annotations = item["annotations"][0].get("result", [])
        elif "predictions" in item and item["predictions"]:
            annotations = item["predictions"][0].get("result", [])

        # Map nhãn hiển thị tiếng Việt (export cũ) → mã value — không có khi chỉ dùng value trong constants
        text_to_value = {lbl["text"]: lbl["value"] for lbl in NER_LABELS if lbl.get("text")}
        spans = []
        for ann in annotations:
            if ann.get("type") != "labels":
                continue
            value = ann.get("value", {})
            label_text = value.get("labels", [None])[0]
            if label_text and value.get("start") is not None:
                # Chuẩn hoá về mã value (Label Studio lưu mã trong labels[]; export cũ có thể map qua text_to_value)
                label_value = text_to_value.get(label_text, label_text)
                if label_value != label_text:
                    logger.debug(f"Mapped: '{label_text}' → '{label_value}'")
                
                spans.append({
                    "start": value["start"],
                    "end": value["end"],
                    "label": label_value
                })

        # Sắp xếp spans theo vị trí
        spans.sort(key=lambda x: x["start"])

        # ── Bước 1: Tách text thành các từ và tính vị trí ký tự ──
        words = []
        word_char_spans = []  # [(char_start, char_end), ...]
        i = 0
        while i < len(text):
            # Bỏ qua khoảng trắng
            if text[i].isspace():
                i += 1
                continue
            # Tìm hết từ (cho đến khoảng trắng tiếp theo)
            j = i
            while j < len(text) and not text[j].isspace():
                j += 1
            words.append(text[i:j])
            word_char_spans.append((i, j))
            i = j

        # ── Bước 2: Gán nhãn BIO cho từng từ (word-level) ──
        word_labels = ["O"] * len(words)

        for span in spans:
            bio_label = span["label"]
            b_label = f"B-{bio_label}"
            i_label = f"I-{bio_label}"

            if b_label not in label2id:
                logger.warning(f"Nhãn '{bio_label}' không có trong label_list. Bỏ qua.")
                continue

            is_first = True
            for w_idx, (w_start, w_end) in enumerate(word_char_spans):
                # Kiểm tra overlap giữa từ và span
                if w_end <= span["start"] or w_start >= span["end"]:
                    continue  # Không overlap

                if is_first:
                    word_labels[w_idx] = b_label
                    is_first = False
                else:
                    word_labels[w_idx] = i_label

        # ── Bước 3: Tokenize từng từ và mở rộng labels cho sub-tokens ──
        all_input_ids = [tokenizer.bos_token_id]  # <s>
        all_labels = [-100]  # Special token → ignored

        for word, word_label in zip(words, word_labels):
            word_tokens = tokenizer.encode(word, add_special_tokens=False)

            if len(word_tokens) == 0:
                continue

            all_input_ids.extend(word_tokens)

            # Token đầu tiên lấy nhãn của từ, các sub-tokens → -100
            label_id = label2id.get(word_label, label2id["O"])
            all_labels.append(label_id)
            all_labels.extend([-100] * (len(word_tokens) - 1))

        # Thêm </s>
        all_input_ids.append(tokenizer.eos_token_id)
        all_labels.append(-100)

        # Truncate nếu quá dài
        max_len = 256
        if len(all_input_ids) > max_len:
            all_input_ids = all_input_ids[:max_len]
            all_labels = all_labels[:max_len]

        attention_mask = [1] * len(all_input_ids)

        processed.append({
            "input_ids": all_input_ids,
            "attention_mask": attention_mask,
            "labels": all_labels
        })

    if skipped > 0:
        logger.warning(f"Đã bỏ qua {skipped} mẫu không có text.")

    logger.info(f"Đã chuyển đổi thành công {len(processed)} mẫu sang định dạng BIO.")
    return processed


def convert_hf_address_standard_to_bio(dataset, tokenizer, label2id: dict, max_len: int = 256) -> list:
    """
    Đọc samples có keys ``tokens``, ``ner_tags`` (như dataset dathuynh* / ner-address-standard-dataset).
    Ánh xạ nhãn về lược đồ BIO trong ``constants.NER_LABELS``.
    """
    processed = []
    features = getattr(dataset, "features", {}) or {}
    ner_col = features.get("ner_tags")
    class_label = getattr(ner_col, "feature", None)
    if hasattr(dataset, "__len__") and hasattr(dataset, "__getitem__"):
        iterator = (dataset[i] for i in range(len(dataset)))
    else:
        iterator = iter(dataset)

    for ex in iterator:
        words = ex.get("tokens") or []
        raw_tags = ex.get("ner_tags") or []
        if len(words) != len(raw_tags) or not words:
            continue

        tag_strs = []
        for t in raw_tags:
            if isinstance(t, int) and class_label is not None and hasattr(class_label, "int2str"):
                tag_strs.append(class_label.int2str(t))
            elif isinstance(t, int):
                tag_strs.append(HF_STANDARD_ID_TO_BIO.get(t, "O"))
            else:
                tag_strs.append(str(t))

        word_labels = []
        for t in tag_strs:
            mapped = HF_STANDARD_BIO_TO_PROJECT.get(t, "O")
            if mapped not in label2id:
                mapped = "O"
            word_labels.append(mapped)

        all_input_ids = [tokenizer.bos_token_id]
        all_labels = [-100]

        for word, word_label in zip(words, word_labels):
            word_tokens = tokenizer.encode(word, add_special_tokens=False)
            if len(word_tokens) == 0:
                continue
            all_input_ids.extend(word_tokens)
            label_id = label2id.get(word_label, label2id["O"])
            all_labels.append(label_id)
            all_labels.extend([-100] * (len(word_tokens) - 1))

        all_input_ids.append(tokenizer.eos_token_id)
        all_labels.append(-100)

        if len(all_input_ids) > max_len:
            all_input_ids = all_input_ids[:max_len]
            all_labels = all_labels[:max_len]

        processed.append({
            "input_ids": all_input_ids,
            "attention_mask": [1] * len(all_input_ids),
            "labels": all_labels,
        })

    logger.info("HF standard dataset → BIO: %d mẫu (sau lọc độ dài/khớp token).", len(processed))
    return processed


def _label_from_bio(label: str) -> str:
    if label == "O":
        return "O"
    return label.split("-", 1)[-1] if "-" in label else label


def validate_required_labels(label_list: list[str]) -> None:
    labels = {_label_from_bio(lb) for lb in label_list if lb != "O"}
    missing = REQUIRED_ENTITY_LABELS - labels
    extras = labels - REQUIRED_ENTITY_LABELS
    if missing or extras:
        raise ValueError(
            f"NER label schema mismatch. Missing={sorted(missing)}, extras={sorted(extras)}; "
            f"required={sorted(REQUIRED_ENTITY_LABELS)}"
        )


def _tokenize_words(text_value: str) -> list[str]:
    return [w for w in re.split(r"\s+", (text_value or "").strip()) if w]


def _weak_bio_from_components(address: str, components: dict, label2id: dict, tokenizer, max_len: int = 256) -> dict:
    words = _tokenize_words(address)
    if not words:
        return {}
    word_labels = ["O"] * len(words)
    priority = ["NUM", "STR", "NHB", "WDS", "DST", "PRO", "BLD", "POI", "ALY", "PCD"]
    for comp_label in priority:
        comp_text = (components or {}).get(comp_label)
        comp_words = _tokenize_words(comp_text or "")
        if not comp_words:
            continue
        n = len(comp_words)
        for i in range(0, len(words) - n + 1):
            if [x.lower() for x in words[i : i + n]] == [x.lower() for x in comp_words]:
                b = f"B-{comp_label}"
                i_tag = f"I-{comp_label}"
                if b not in label2id:
                    continue
                word_labels[i] = b
                for j in range(1, n):
                    word_labels[i + j] = i_tag
                break

    all_input_ids = [tokenizer.bos_token_id]
    all_labels = [-100]
    for word, word_label in zip(words, word_labels):
        word_tokens = tokenizer.encode(word, add_special_tokens=False)
        if not word_tokens:
            continue
        all_input_ids.extend(word_tokens)
        all_labels.append(label2id.get(word_label, label2id["O"]))
        all_labels.extend([-100] * (len(word_tokens) - 1))

    all_input_ids.append(tokenizer.eos_token_id)
    all_labels.append(-100)
    if len(all_input_ids) > max_len:
        all_input_ids = all_input_ids[:max_len]
        all_labels = all_labels[:max_len]
    return {"input_ids": all_input_ids, "attention_mask": [1] * len(all_input_ids), "labels": all_labels}


def load_ground_truth_weak_bio_samples(tokenizer, label2id: dict, limit: int = 10000) -> list:
    sql = text(
        """
        SELECT standardized_address, address_components
        FROM prq.address_clean_corpus
        WHERE source_type = 'QUEUE_STANDARDIZED'
          AND address_components IS NOT NULL
          AND standardized_address IS NOT NULL
          AND length(trim(standardized_address)) > 5
        ORDER BY updated_at DESC NULLS LAST, id DESC
        LIMIT :limit
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"limit": int(limit)}).mappings().all()
    finally:
        session.close()

    out = []
    for r in rows:
        sample = _weak_bio_from_components(
            r["standardized_address"],
            r["address_components"] or {},
            label2id,
            tokenizer,
        )
        if sample:
            out.append(sample)
    logger.info("Ground-truth weak BIO samples: %d", len(out))
    return out


def validate_conversion(data: list, processed: list, tokenizer, id2label: dict, n_samples: int = 5):
    """In ra một vài mẫu để kiểm tra nhãn BIO có đúng không."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  KIỂM TRA CHUYỂN ĐỔI BIO ({n_samples} mẫu đầu)")
    logger.info(f"{'='*60}")

    for i in range(min(n_samples, len(processed))):
        sample = processed[i]
        text = data[i].get("data", {}).get("text", "")
        tokens = tokenizer.convert_ids_to_tokens(sample["input_ids"])
        labels = [id2label.get(l, "IGN") if l != -100 else "---" for l in sample["labels"]]

        logger.info(f"\n--- Mẫu {i+1}: \"{text[:80]}...\"")
        for tok, lab in zip(tokens, labels):
            if lab not in ("---", "O"):
                logger.info(f"  {tok:20s} → {lab}")


# ──────────────────────────────────────────────────────────────────────────────
# Bước 2: Compute Metrics cho Trainer (seqeval)
# ──────────────────────────────────────────────────────────────────────────────

def build_compute_metrics(id2label: dict):
    """Trả về hàm compute_metrics tương thích với HuggingFace Trainer."""

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=2)

        # Chuyển về danh sách string labels, bỏ qua -100
        true_labels = []
        pred_labels = []

        for pred_seq, label_seq in zip(predictions, labels):
            true_seq = []
            pred_seq_clean = []
            for p, l in zip(pred_seq, label_seq):
                if l == -100:
                    continue
                true_seq.append(id2label[l])
                pred_seq_clean.append(id2label[p])
            true_labels.append(true_seq)
            pred_labels.append(pred_seq_clean)

        # Tính metrics bằng seqeval
        f1 = f1_score(true_labels, pred_labels)
        precision = precision_score(true_labels, pred_labels)
        recall = recall_score(true_labels, pred_labels)

        return {
            "f1": f1,
            "precision": precision,
            "recall": recall,
        }

    return compute_metrics


def _compute_token_accuracy(predictions: np.ndarray, labels: np.ndarray) -> float:
    """Return token-level accuracy while ignoring padded tokens."""
    correct = 0
    total = 0

    for pred_seq, label_seq in zip(predictions, labels):
        for pred_id, label_id in zip(pred_seq, label_seq):
            if label_id == -100:
                continue
            total += 1
            if pred_id == label_id:
                correct += 1

    return correct / total if total > 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Bước 3: Train Model
# ──────────────────────────────────────────────────────────────────────────────

def train_model(
    json_path: Optional[str] = None,
    output_dir: str = "models/phobert-ner-vn",
    epochs: int = 15,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    eval_split: float = 0.2,
    seed: int = 42,
    hf_dataset: Optional[str] = None,
    hf_max_train_samples: int = 50_000,
    hf_max_eval_samples: int = 5_000,
    include_ground_truth: bool = False,
    gt_max_train_samples: int = 10_000,
):
    """
    Huấn luyện PhoBERT NER: either Label Studio JSON (``json_path``) hoặc dataset HF
    (``hf_dataset``, ví dụ dathuynh1108/ner-address-standard-dataset).
    """
    use_hf = bool(hf_dataset)
    if use_hf == bool(json_path):
        raise ValueError("Chỉ định đúng một nguồn: json_path (Label Studio) hoặc hf_dataset (Hugging Face).")

    label_list = get_ner_label_list()
    validate_required_labels(label_list)
    label2id = {l: i for i, l in enumerate(label_list)}
    id2label = {i: l for i, l in enumerate(label_list)}
    logger.info(f"Số nhãn BIO: {len(label_list)} ({label_list})")

    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", trust_remote_code=True)

    if use_hf:
        from datasets import load_dataset

        logger.info(
            "Tải HF %s — train[:%s], test[:%s]…",
            hf_dataset,
            hf_max_train_samples,
            hf_max_eval_samples,
        )
        used_streaming = False
        try:
            train_raw = load_dataset(hf_dataset, split=f"train[:{hf_max_train_samples}]")
            eval_raw = load_dataset(hf_dataset, split=f"test[:{hf_max_eval_samples}]")
        except Exception as exc:
            logger.warning(
                "HF load_dataset mặc định lỗi (%s). Fallback sang streaming=True để tránh DatasetGenerationError.",
                exc,
            )
            used_streaming = True
            train_raw = list(islice(load_dataset(hf_dataset, split="train", streaming=True), hf_max_train_samples))
            eval_raw = list(islice(load_dataset(hf_dataset, split="test", streaming=True), hf_max_eval_samples))

        train_data = convert_hf_address_standard_to_bio(train_raw, tokenizer, label2id)
        eval_data = convert_hf_address_standard_to_bio(eval_raw, tokenizer, label2id)
        if include_ground_truth:
            gt_train = load_ground_truth_weak_bio_samples(
                tokenizer=tokenizer,
                label2id=label2id,
                limit=gt_max_train_samples,
            )
            train_data.extend(gt_train)
            logger.info("Merged HF + ground_truth weak labels => train=%d", len(train_data))
        if len(train_data) == 0:
            logger.error("Không chuyển đổi được mẫu train từ HF. Kiểm tra schema dataset.")
            return
        if len(eval_data) == 0:
            logger.warning("Eval HF rỗng — tách ngẫu nhiên từ train.")
            np.random.seed(seed)
            ix = np.random.permutation(len(train_data))
            split_idx = int(len(train_data) * (1 - eval_split))
            eval_data = [train_data[i] for i in ix[split_idx:]]
            train_data = [train_data[i] for i in ix[:split_idx]]
        logger.info("Train: %d mẫu | Eval: %d mẫu (HF)", len(train_data), len(eval_data))
        data_notes = (
            f"hf_dataset={hf_dataset};train_cap={hf_max_train_samples};"
            f"eval_cap={hf_max_eval_samples};streaming={used_streaming}"
        )
    else:
        logger.info(f"Đọc dữ liệu từ {json_path}...")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Tổng số mẫu: {len(data)}")

        processed = convert_labelstudio_to_bio(data, tokenizer, label2id)

        if len(processed) == 0:
            logger.error("Không có mẫu nào được chuyển đổi thành công. Kiểm tra lại file JSON.")
            return

        validate_conversion(data, processed, tokenizer, id2label)

        np.random.seed(seed)
        indices = np.random.permutation(len(processed))
        split_idx = int(len(processed) * (1 - eval_split))

        train_data = [processed[i] for i in indices[:split_idx]]
        eval_data = [processed[i] for i in indices[split_idx:]]
        logger.info(f"Train: {len(train_data)} mẫu | Eval: {len(eval_data)} mẫu")
        data_notes = f"labelstudio={json_path}"

    # 6. Tạo HuggingFace Dataset
    def to_hf_dataset(items):
        return Dataset.from_dict({
            "input_ids": [x["input_ids"] for x in items],
            "attention_mask": [x["attention_mask"] for x in items],
            "labels": [x["labels"] for x in items],
        })

    train_dataset = to_hf_dataset(train_data)
    eval_dataset = to_hf_dataset(eval_data)

    # 7. Load model
    model = AutoModelForTokenClassification.from_pretrained(
        "vinai/phobert-base",
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id
    )

    # 8. Training Arguments
    ta_kwargs = dict(
        output_dir=output_dir,
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        num_train_epochs=epochs,
        weight_decay=0.01,
        warmup_ratio=0.1,
        save_total_limit=3,
        push_to_hub=False,
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        seed=seed,
        fp16=torch.cuda.is_available(),
    )
    sig = inspect.signature(TrainingArguments.__init__)
    if "report_to" in sig.parameters:
        # Avoid wandb/tensorboard login prompts on machines without WANDB_API_KEY
        ta_kwargs["report_to"] = []
    if "evaluation_strategy" in sig.parameters:
        ta_kwargs["evaluation_strategy"] = "epoch"
    elif "eval_strategy" in sig.parameters:
        ta_kwargs["eval_strategy"] = "epoch"
    if "save_strategy" in sig.parameters:
        ta_kwargs["save_strategy"] = "epoch"
    training_args = TrainingArguments(**ta_kwargs)

    # 9. Data Collator (Dynamic padding)
    data_collator = DataCollatorForTokenClassification(
        tokenizer=tokenizer,
        padding=True,
        label_pad_token_id=-100
    )

    # 10. Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=build_compute_metrics(id2label),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
    )

    # 11. Train!
    logger.info("=" * 60)
    logger.info("  KHỞI ĐỘNG HUẤN LUYỆN PhoBERT NER")
    logger.info(f"  Epochs: {epochs} | Batch: {batch_size} | LR: {learning_rate}")
    logger.info(f"  Device: {'GPU' if torch.cuda.is_available() else 'CPU'}")
    logger.info("=" * 60)

    train_result = trainer.train()

    # 12. Lưu model + tokenizer
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # 13. Eval cuối cùng
    eval_results = trainer.evaluate()
    logger.info(f"\n{'='*60}")
    logger.info(f"  KẾT QUẢ ĐÁNH GIÁ CUỐI CÙNG")
    logger.info(f"{'='*60}")
    for key, value in eval_results.items():
        logger.info(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")

    # 14. In classification report chi tiết
    logger.info("\n  Classification Report (seqeval):")
    predictions, labels, _ = trainer.predict(eval_dataset)
    predictions = np.argmax(predictions, axis=2)
    token_accuracy = _compute_token_accuracy(predictions, labels)

    true_labels = []
    pred_labels = []
    for pred_seq, label_seq in zip(predictions, labels):
        true_seq = []
        pred_seq_clean = []
        for p, l in zip(pred_seq, label_seq):
            if l == -100:
                continue
            true_seq.append(id2label[l])
            pred_seq_clean.append(id2label[p])
        true_labels.append(true_seq)
        pred_labels.append(pred_seq_clean)

    report = classification_report(true_labels, pred_labels, digits=4)
    logger.info(f"\n{report}")

    try:
        record_training_history(
            version=Path(output_dir).name or "phobert-ner-vn",
            accuracy=round(token_accuracy * 100, 2),
            f1_score=round(float(eval_results.get("eval_f1", 0.0)) * 100, 2),
            loss=round(float(train_result.training_loss), 6),
            samples_count=len(train_data),
            notes=(
                f"{data_notes}; epochs={epochs}; batch_size={batch_size}; lr={learning_rate}; "
                f"eval_split={eval_split}; eval_loss={float(eval_results.get('eval_loss', 0.0)):.6f}"
            ),
        )
        logger.info("Đã ghi training_history vào DB.")
    except Exception as exc:
        logger.warning("Không thể ghi training_history vào DB: %s", exc)

    # 15. Lưu training log
    log_path = os.path.join(output_dir, "training_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "train_loss": train_result.training_loss,
            "eval_results": eval_results,
            "token_accuracy": float(token_accuracy),
            "label_list": label_list,
            "n_train": len(train_data),
            "n_eval": len(eval_data),
            "epochs": epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "data_source": data_notes,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\nModel đã được lưu tại: {output_dir}")
    logger.info(f"Training log: {log_path}")
    logger.info("HOÀN TẤT HUẤN LUYỆN!")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện PhoBERT NER cho địa chỉ Việt Nam")
    parser.add_argument("--data", default=None, help="JSON export từ Label Studio (bỏ qua nếu dùng --hf-dataset)")
    parser.add_argument("--hf-dataset", default=None, help="VD: dathuynh1108/ner-address-standard-dataset")
    parser.add_argument("--hf-max-train", type=int, default=50_000, help="Giới hạn mẫu train từ HF")
    parser.add_argument("--hf-max-eval", type=int, default=5_000, help="Giới hạn mẫu test từ HF (split test)")
    parser.add_argument("--output", default="models/phobert-ner-vn", help="Thư mục lưu model")
    parser.add_argument("--epochs", type=int, default=15, help="Số epoch huấn luyện")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--eval-split", type=float, default=0.2, help="Tỷ lệ eval (0.2 = 20%) — với Label Studio")
    parser.add_argument("--validate-only", action="store_true", help="Chỉ validate chuyển đổi, không train")
    parser.add_argument("--include-ground-truth", action="store_true", help="Trộn thêm weak labels từ address_clean_corpus")
    parser.add_argument("--gt-max-train", type=int, default=10000, help="Giới hạn mẫu weak labels ground_truth")
    args = parser.parse_args()

    if args.validate_only:
        if not args.data:
            parser.error("--validate-only cần --data")
        # Chỉ chạy validate để kiểm tra chuyển đổi BIO
        label_list = get_ner_label_list()
        label2id = {l: i for i, l in enumerate(label_list)}
        id2label = {i: l for i, l in enumerate(label_list)}
        tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", trust_remote_code=True)

        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)

        processed = convert_labelstudio_to_bio(data, tokenizer, label2id)
        validate_conversion(data, processed, tokenizer, id2label, n_samples=10)
    elif args.hf_dataset:
        train_model(
            json_path=None,
            output_dir=args.output,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            eval_split=args.eval_split,
            hf_dataset=args.hf_dataset,
            hf_max_train_samples=args.hf_max_train,
            hf_max_eval_samples=args.hf_max_eval,
            include_ground_truth=args.include_ground_truth,
            gt_max_train_samples=args.gt_max_train,
        )
    else:
        if not args.data:
            parser.error("Cần --data hoặc --hf-dataset")
        train_model(
            json_path=args.data,
            output_dir=args.output,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            eval_split=args.eval_split,
            include_ground_truth=args.include_ground_truth,
            gt_max_train_samples=args.gt_max_train,
        )
