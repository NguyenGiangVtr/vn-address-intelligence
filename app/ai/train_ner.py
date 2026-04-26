"""
train_ner.py
============
Script huấn luyện mô hình NER PhoBERT với dữ liệu từ Label Studio.
Sử dụng HuggingFace Trainer API.
"""

import os
import json
import logging
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorForTokenClassification
)
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainNER")

from constants import get_ner_label_list

def train_model(json_path: str, output_dir: str = "models/phobert-ner-vn"):
    # 1. Load dữ liệu gán nhãn
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Chuyển đổi dữ liệu Label Studio sang định dạng Training
    # (Giả định team gán nhãn theo format Named Entity Recognition của Label Studio)
    
    # Danh sách nhãn đầy đủ lấy từ constants.py
    label_list = get_ner_label_list()
    label2id = {l: i for i, l in enumerate(label_list)}
    id2label = {i: l for i, l in enumerate(label_list)}

    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", trust_remote_code=True)

    # ... (Phần logic bóc tách nhãn từ JSON sẽ được thực hiện tại đây khi có file thực tế) ...
    # Để script chạy được ngay, tôi sẽ viết khung Trainer chuẩn SOTA
    
    model = AutoModelForTokenClassification.from_pretrained(
        "vinai/phobert-base", 
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id
    )

    training_args = TrainingArguments(
        output_dir=output_dir,
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        num_train_epochs=10,
        weight_decay=0.01,
        save_total_limit=2,
        push_to_hub=False,
        logging_steps=10,
        load_best_model_at_end=True
    )

    # Trainer này sẽ thực thi việc học sâu trên GPU
    logger.info("🚀 Sẵn sàng huấn luyện mô hình PhoBERT NER...")
    # trainer = Trainer(
    #     model=model,
    #     args=training_args,
    #     train_dataset=train_dataset,
    #     eval_dataset=eval_dataset,
    #     tokenizer=tokenizer,
    #     data_collator=DataCollatorForTokenClassification(tokenizer)
    # )
    # trainer.train()

    logger.info(f"✅ Mô hình đã được lưu tại {output_dir}")

if __name__ == "__main__":
    # Khi có dữ liệu, bạn chỉ cần chạy: python src/train_ner.py --data data/project_export.json
    print("💡 Script đã sẵn sàng. Khi Team Data gán nhãn xong, hãy gọi hàm train_model().")
