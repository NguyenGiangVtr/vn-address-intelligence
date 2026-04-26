"""
train_ner.py
============
Script huấn luyện mô hình NER PhoBERT với dữ liệu từ Label Studio.
Sử dụng HuggingFace Trainer API + seqeval để đánh giá.

Cách chạy:
    python app/ai/train_ner.py --data data/labeled_export.json
    python app/ai/train_ner.py --data data/labeled_export.json --epochs 20 --lr 3e-5
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

import torch
import numpy as np
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

# Đảm bảo import từ cùng package
sys.path.insert(0, str(Path(__file__).parent))
from constants import get_ner_label_list

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainNER")

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

        # Lọc chỉ lấy labels type
        spans = []
        for ann in annotations:
            if ann.get("type") != "labels":
                continue
            value = ann.get("value", {})
            label = value.get("labels", [None])[0]
            if label and value.get("start") is not None:
                spans.append({
                    "start": value["start"],
                    "end": value["end"],
                    "label": label
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


# ──────────────────────────────────────────────────────────────────────────────
# Bước 3: Train Model
# ──────────────────────────────────────────────────────────────────────────────

def train_model(
    json_path: str,
    output_dir: str = "models/phobert-ner-vn",
    epochs: int = 15,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    eval_split: float = 0.2,
    seed: int = 42
):
    """
    Huấn luyện mô hình PhoBERT NER với dữ liệu từ Label Studio.

    Parameters
    ----------
    json_path : str
        Đường dẫn file JSON export từ Label Studio
    output_dir : str
        Thư mục lưu model fine-tuned
    epochs : int
        Số epoch huấn luyện
    batch_size : int
        Batch size (giảm nếu thiếu VRAM)
    learning_rate : float
        Learning rate (2e-5 là chuẩn cho BERT fine-tuning)
    eval_split : float
        Tỷ lệ dữ liệu dành cho evaluation (0.2 = 20%)
    seed : int
        Random seed để tái tạo kết quả
    """
    # 1. Load dữ liệu gán nhãn
    logger.info(f"Đọc dữ liệu từ {json_path}...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Tổng số mẫu: {len(data)}")

    # 2. Chuẩn bị label mapping từ constants.py
    label_list = get_ner_label_list()
    label2id = {l: i for i, l in enumerate(label_list)}
    id2label = {i: l for i, l in enumerate(label_list)}
    logger.info(f"Số nhãn BIO: {len(label_list)} ({label_list})")

    # 3. Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", trust_remote_code=True)

    # 4. Chuyển đổi Label Studio → BIO
    processed = convert_labelstudio_to_bio(data, tokenizer, label2id)

    if len(processed) == 0:
        logger.error("Không có mẫu nào được chuyển đổi thành công. Kiểm tra lại file JSON.")
        return

    # Validate chuyển đổi
    validate_conversion(data, processed, tokenizer, id2label)

    # 5. Chia Train / Eval
    np.random.seed(seed)
    indices = np.random.permutation(len(processed))
    split_idx = int(len(processed) * (1 - eval_split))

    train_data = [processed[i] for i in indices[:split_idx]]
    eval_data = [processed[i] for i in indices[split_idx:]]
    logger.info(f"Train: {len(train_data)} mẫu | Eval: {len(eval_data)} mẫu")

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
    training_args = TrainingArguments(
        output_dir=output_dir,
        evaluation_strategy="epoch",
        save_strategy="epoch",
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
        fp16=torch.cuda.is_available(),  # Mixed precision nếu có GPU
    )

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

    # 15. Lưu training log
    log_path = os.path.join(output_dir, "training_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "train_loss": train_result.training_loss,
            "eval_results": eval_results,
            "label_list": label_list,
            "n_train": len(train_data),
            "n_eval": len(eval_data),
            "epochs": epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\nModel đã được lưu tại: {output_dir}")
    logger.info(f"Training log: {log_path}")
    logger.info("HOÀN TẤT HUẤN LUYỆN!")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện PhoBERT NER cho địa chỉ Việt Nam")
    parser.add_argument("--data", required=True, help="Đường dẫn file JSON export từ Label Studio")
    parser.add_argument("--output", default="models/phobert-ner-vn", help="Thư mục lưu model")
    parser.add_argument("--epochs", type=int, default=15, help="Số epoch huấn luyện")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--eval-split", type=float, default=0.2, help="Tỷ lệ eval (0.2 = 20%)")
    parser.add_argument("--validate-only", action="store_true", help="Chỉ validate chuyển đổi, không train")
    args = parser.parse_args()

    if args.validate_only:
        # Chỉ chạy validate để kiểm tra chuyển đổi BIO
        label_list = get_ner_label_list()
        label2id = {l: i for i, l in enumerate(label_list)}
        id2label = {i: l for i, l in enumerate(label_list)}
        tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", trust_remote_code=True)

        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)

        processed = convert_labelstudio_to_bio(data, tokenizer, label2id)
        validate_conversion(data, processed, tokenizer, id2label, n_samples=10)
    else:
        train_model(
            json_path=args.data,
            output_dir=args.output,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            eval_split=args.eval_split
        )
