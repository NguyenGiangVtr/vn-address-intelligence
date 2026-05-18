# Hướng dẫn Lệnh Training PhoBERT NER

## Lệnh cơ bản

```bash
python -m app.ai.train_ner --from-prelabeler --min-prelabeler-samples 50 --epochs 10
```

---

## Giải thích các tham số

### 1. `--from-prelabeler`
**Loại:** Flag (boolean)  
**Mặc định:** `False`  
**Ý nghĩa:** Kích hoạt chế độ huấn luyện từ dữ liệu PreLabeler Cases

**Chi tiết:**
- Khi có flag này, script sẽ đọc dữ liệu từ bảng `ai.prelabeler_testcases` trong PostgreSQL
- Chỉ lấy các mẫu có `test_result->>'passed' = true` (mẫu đạt chuẩn validation)
- Dữ liệu được chuyển đổi tự động sang định dạng BIO tokens cho PhoBERT

**Ví dụ:**
```bash
# Bật chế độ prelabeler
python -m app.ai.train_ner --from-prelabeler

# Không dùng prelabeler (dùng Label Studio hoặc HuggingFace dataset)
python -m app.ai.train_ner --data data/labeled_export.json
```

---

### 2. `--min-prelabeler-samples 50`
**Loại:** Integer  
**Mặc định:** `50`  
**Ý nghĩa:** Số lượng mẫu tối thiểu cần có để bắt đầu huấn luyện

**Chi tiết:**
- Script sẽ kiểm tra số lượng mẫu đạt chuẩn trong database
- Nếu `số_mẫu < min-prelabeler-samples`, script sẽ báo lỗi và dừng lại
- Đảm bảo có đủ dữ liệu để mô hình học được patterns có ý nghĩa
- Khuyến nghị: tối thiểu 50-100 mẫu cho kết quả tốt

**Ví dụ:**
```bash
# Yêu cầu tối thiểu 100 mẫu
python -m app.ai.train_ner --from-prelabeler --min-prelabeler-samples 100

# Yêu cầu tối thiểu 30 mẫu (cho testing)
python -m app.ai.train_ner --from-prelabeler --min-prelabeler-samples 30
```

---

### 3. `--epochs 10`
**Loại:** Integer  
**Mặc định:** `15`  
**Ý nghĩa:** Số lượng epoch (vòng lặp) huấn luyện qua toàn bộ dataset

**Chi tiết:**
- Mỗi epoch = 1 lần duyệt qua toàn bộ dữ liệu training
- Nhiều epochs → mô hình học kỹ hơn, nhưng có thể overfitting
- Ít epochs → mô hình chưa học đủ, underfitting
- Khuyến nghị:
  - **Dữ liệu nhỏ (< 100 mẫu):** 10-15 epochs
  - **Dữ liệu vừa (100-500 mẫu):** 8-12 epochs
  - **Dữ liệu lớn (> 500 mẫu):** 5-10 epochs

**Ví dụ:**
```bash
# Training nhanh (5 epochs)
python -m app.ai.train_ner --from-prelabeler --epochs 5

# Training kỹ (20 epochs)
python -m app.ai.train_ner --from-prelabeler --epochs 20
```

---

## Các tham số bổ sung (optional)

### `--batch-size 16`
**Mặc định:** `16`  
**Ý nghĩa:** Số lượng mẫu xử lý cùng lúc trong mỗi bước training

**Chi tiết:**
- Batch size lớn → training nhanh hơn, nhưng tốn nhiều RAM/VRAM
- Batch size nhỏ → ít tốn bộ nhớ, nhưng training chậm hơn
- Nếu gặp lỗi `Out of Memory`, giảm batch size xuống

**Ví dụ:**
```bash
# GPU yếu hoặc RAM ít
python -m app.ai.train_ner --from-prelabeler --batch-size 8

# GPU mạnh
python -m app.ai.train_ner --from-prelabeler --batch-size 32
```

---

### `--lr 2e-5` (Learning Rate)
**Mặc định:** `2e-5` (0.00002)  
**Ý nghĩa:** Tốc độ học của mô hình

**Chi tiết:**
- Learning rate cao → học nhanh, nhưng có thể bỏ lỡ optimal point
- Learning rate thấp → học chậm, nhưng ổn định hơn
- Khuyến nghị cho PhoBERT fine-tuning: `1e-5` đến `5e-5`

**Ví dụ:**
```bash
# Learning rate thấp (ổn định)
python -m app.ai.train_ner --from-prelabeler --lr 1e-5

# Learning rate cao (học nhanh)
python -m app.ai.train_ner --from-prelabeler --lr 5e-5
```

---

### `--merge-labelstudio data/labeled_export.json`
**Mặc định:** `None`  
**Ý nghĩa:** Kết hợp dữ liệu prelabeler với Label Studio export

**Chi tiết:**
- Chỉ hoạt động khi có `--from-prelabeler`
- Tăng quy mô và đa dạng hóa dữ liệu training
- Dữ liệu từ cả hai nguồn sẽ được merge lại trước khi training

**Ví dụ:**
```bash
python -m app.ai.train_ner \
  --from-prelabeler \
  --merge-labelstudio data/labeled_export.json \
  --epochs 10
```

---

### `--output models/phobert-ner-vn`
**Mặc định:** `models/phobert-ner-vn`  
**Ý nghĩa:** Thư mục lưu checkpoint sau khi training

**Chi tiết:**
- Checkpoint bao gồm: model weights, tokenizer config, training_log.json
- Tên thư mục thường theo format: `phobert-ner-vn-YYYYMMDD-HHMMSS`
- Metadata được ghi vào `ath.training_history` table

**Ví dụ:**
```bash
python -m app.ai.train_ner \
  --from-prelabeler \
  --output models/phobert-ner-vn-20260516-184500
```

---

### `--eval-split 0.2`
**Mặc định:** `0.2` (20%)  
**Ý nghĩa:** Tỷ lệ dữ liệu dùng để validation

**Chi tiết:**
- 0.2 = 20% dữ liệu dùng để đánh giá, 80% dùng để training
- Validation set giúp theo dõi overfitting
- Khuyến nghị: 0.15 - 0.25 (15% - 25%)

**Ví dụ:**
```bash
# Dùng 15% cho validation
python -m app.ai.train_ner --from-prelabeler --eval-split 0.15
```

---

## Thứ tự công việc (Workflow)

Khi chạy lệnh `python -m app.ai.train_ner --from-prelabeler --min-prelabeler-samples 50 --epochs 10`, script thực hiện các bước sau:

### **Bước 1: Khởi tạo & Validation**
```
1.1. Parse command-line arguments
1.2. Load NER label list từ constants (B-NUM, I-NUM, B-STR, ...)
1.3. Validate required labels (NUM, STR, WDS, DST, PRO, ...)
1.4. Tạo label2id và id2label mappings
1.5. Load PhoBERT tokenizer từ "vinai/phobert-base"
```

### **Bước 2: Load dữ liệu từ PreLabeler Cases**
```sql
2.1. Kết nối PostgreSQL database
2.2. Query bảng ai.prelabeler_testcases:
    SELECT id, input, expected, test_result, created_at
    FROM ai.prelabeler_testcases
    WHERE expected IS NOT NULL
      AND jsonb_array_length(expected) > 0
      AND (test_result->>'passed')::boolean = true
    ORDER BY created_at DESC

2.3. Kiểm tra số lượng mẫu:
    - Nếu count < min_prelabeler_samples (50) → Raise error
    - Nếu count >= 50 → Tiếp tục

2.4. Log: "Found {count} prelabeler cases (only_passed=True)"
```

### **Bước 3: Chuyển đổi sang Label Studio format**
```
3.1. Với mỗi prelabeler case:
    - Input: raw_address = "268 Lý Thường Kiệt, Phường 14, Quận 10, TP.HCM"
    - Expected: [{"label": "NUM", "text": "268"}, {"label": "STR", "text": "Lý Thường Kiệt"}, ...]

3.2. Tính character offset cho mỗi entity:
    - Tìm vị trí start/end của "268" trong raw_address → (0, 3)
    - Tìm vị trí start/end của "Lý Thường Kiệt" → (4, 18)
    - ...

3.3. Tạo Label Studio annotation format:
    {
      "data": {"text": "268 Lý Thường Kiệt, ..."},
      "annotations": [{
        "result": [
          {"value": {"start": 0, "end": 3, "text": "268", "labels": ["NUM"]}},
          {"value": {"start": 4, "end": 18, "text": "Lý Thường Kiệt", "labels": ["STR"]}},
          ...
        ]
      }]
    }

3.4. Log: "Converted {count} prelabeler cases to Label Studio format"
```

### **Bước 4: Chuyển đổi sang BIO tokens**
```
4.1. Với mỗi Label Studio item:
    - Tokenize raw_address bằng PhoBERT tokenizer
    - Input: "268 Lý Thường Kiệt"
    - Tokens: ["268", "Lý", "Thường", "Kiệt"]
    - Sub-tokens: ["268", "Lý", "▁Thường", "▁Kiệt"]

4.2. Gán nhãn BIO cho từng token:
    - "268" → B-NUM (Begin-NUM)
    - "Lý" → B-STR (Begin-STR)
    - "▁Thường" → I-STR (Inside-STR)
    - "▁Kiệt" → I-STR (Inside-STR)

4.3. Convert sang IDs:
    - input_ids: [268_id, Lý_id, Thường_id, Kiệt_id]
    - labels: [B-NUM_id, B-STR_id, I-STR_id, I-STR_id]
    - attention_mask: [1, 1, 1, 1]

4.4. Kết quả: List[dict] với keys [input_ids, attention_mask, labels]
```

### **Bước 5: Merge với Label Studio (nếu có --merge-labelstudio)**
```
5.1. Nếu có --merge-labelstudio:
    - Load Label Studio JSON file
    - Convert sang BIO tokens (tương tự bước 4)
    - Merge: train_data = prelabeler_data + labelstudio_data
    - Log: "Merged {count} Label Studio samples"
```

### **Bước 6: Split Train/Eval**
```
6.1. Shuffle dữ liệu (seed=42 để reproducible)
6.2. Split theo tỷ lệ eval_split (mặc định 0.2):
    - 80% → train_dataset
    - 20% → eval_dataset
6.3. Convert sang HuggingFace Dataset format
6.4. Log: "Train: {train_count} samples, Eval: {eval_count} samples"
```

### **Bước 7: Load Model & Setup Training**
```
7.1. Load PhoBERT model:
    - AutoModelForTokenClassification.from_pretrained("vinai/phobert-base")
    - num_labels = len(label_list)
    - id2label, label2id mappings

7.2. Setup TrainingArguments:
    - output_dir = "models/phobert-ner-vn"
    - num_train_epochs = 10
    - per_device_train_batch_size = 16
    - learning_rate = 2e-5
    - evaluation_strategy = "epoch"
    - save_strategy = "epoch"
    - load_best_model_at_end = True
    - metric_for_best_model = "f1"

7.3. Setup Trainer:
    - model, tokenizer, data_collator
    - train_dataset, eval_dataset
    - compute_metrics (seqeval: precision, recall, f1, accuracy)
```

### **Bước 8: Training Loop**
```
8.1. Với mỗi epoch (1 → 10):
    8.1.1. Training phase:
        - Duyệt qua train_dataset theo batch (16 samples/batch)
        - Forward pass: tính predictions
        - Backward pass: tính gradients
        - Update weights
        - Log: loss, learning_rate

    8.1.2. Evaluation phase (sau mỗi epoch):
        - Duyệt qua eval_dataset
        - Tính predictions
        - So sánh với ground truth labels
        - Tính metrics: precision, recall, f1, accuracy
        - Log: eval_loss, eval_f1, eval_precision, eval_recall

    8.1.3. Save checkpoint:
        - Nếu f1 score tốt hơn best_f1 → save model
        - Checkpoint: {output_dir}/checkpoint-{epoch}/

8.2. Early stopping (nếu f1 không cải thiện sau 3 epochs)
```

### **Bước 9: Save Final Model & Metadata**
```
9.1. Load best checkpoint (epoch có f1 cao nhất)
9.2. Save final model:
    - model.save_pretrained(output_dir)
    - tokenizer.save_pretrained(output_dir)

9.3. Tạo training_log.json:
    {
      "model": "vinai/phobert-base",
      "num_labels": 23,
      "train_samples": 120,
      "eval_samples": 30,
      "epochs": 10,
      "batch_size": 16,
      "learning_rate": 2e-5,
      "eval_f1": 0.9234,
      "eval_precision": 0.9156,
      "eval_recall": 0.9314,
      "eval_accuracy": 0.9678,
      "eval_loss": 0.1573,
      "git_commit": "abc123def",
      "timestamp": "2026-05-16T18:45:00"
    }

9.4. Ghi vào database (ath.training_history):
    INSERT INTO ath.training_history (
      model_name, version, accuracy, f1_score, precision_score,
      recall_score, loss, samples_count, notes, created_at
    ) VALUES (...)

9.5. Log: "Training completed! Model saved to {output_dir}"
```

### **Bước 10: Cleanup**
```
10.1. Đóng database connection
10.2. Xóa temporary checkpoints (giữ lại best model)
10.3. Print final summary:
     - Total training time
     - Best F1 score
     - Model location
```

---

## Ví dụ Output Log

```
18:45:00.123 [INFO] Số nhãn BIO: 23 (['O', 'B-NUM', 'I-NUM', 'B-STR', ...])
18:45:01.456 [INFO] Loading data from ai.prelabeler_testcases...
18:45:02.789 [INFO] Found 120 prelabeler cases (only_passed=True)
18:45:03.012 [INFO] Converted 120 prelabeler cases to Label Studio format
18:45:05.234 [INFO] Train: 96 samples, Eval: 24 samples
18:45:10.567 [INFO] Epoch 1/10 - loss: 0.8234, eval_f1: 0.7123
18:45:15.890 [INFO] Epoch 2/10 - loss: 0.5678, eval_f1: 0.8234
...
18:50:30.123 [INFO] Epoch 10/10 - loss: 0.1573, eval_f1: 0.9234
18:50:35.456 [INFO] Training completed! Model saved to models/phobert-ner-vn
18:50:35.789 [INFO] Best F1: 0.9234 (Epoch 10)
```

---

## Tóm tắt

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `--from-prelabeler` | flag | Dùng dữ liệu từ PreLabeler Cases |
| `--min-prelabeler-samples` | 50 | Tối thiểu 50 mẫu đạt chuẩn |
| `--epochs` | 10 | Huấn luyện 10 vòng lặp |
| `--batch-size` | 16 (default) | 16 mẫu/batch |
| `--lr` | 2e-5 (default) | Learning rate = 0.00002 |
| `--eval-split` | 0.2 (default) | 20% dữ liệu cho validation |
| `--output` | models/phobert-ner-vn (default) | Thư mục lưu model |

**Thời gian ước tính:**
- CPU: ~5-15 phút (tùy số mẫu)
- GPU: ~2-5 phút (tùy số mẫu)

**Kết quả:**
- Model checkpoint: `models/phobert-ner-vn/`
- Training log: `models/phobert-ner-vn/training_log.json`
- Database record: `ath.training_history` table
