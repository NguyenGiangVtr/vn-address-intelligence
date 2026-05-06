# 📝 Model 1: NER Entities (PhoBERT Token Classification)

**File:** `01-NER_Entities.md`  
**Thành phần:** `AddressNER` (app/ai/models/ner_model.py)  
**Cập nhật:** 2026-05-05

---

## 🎯 Mục đích

Bóc tách (extract) các thành phần địa chỉ từ văn bản thô thành các nhãn có nghĩa:
- **Số nhà** (NUM), **Tên đường** (STR), **Tòa nhà** (BLD), **Hẻm** (ALY)
- **Phường/Xã** (WDS), **Quận/Huyện** (DST), **Tỉnh** (PRO)
- **Khu phố** (NHB), **Mốc/Cửa hàng** (POI), **Plus Code** (PCD)

---

## 📥 INPUT: Dữ liệu đầu vào

### Nguồn dữ liệu
- **Raw text:** `prq.address_cleansing_queue.raw_address` hoặc `street_address`
- **Định dạng:** UTF-8 string, tối đa 512 ký tự/dòng
- **Ví dụ:**
  ```
  "268 Lý Thường Kiệt, Phường 14, Quận 10, TP.HCM"
  "Hẻm 45/12 Đường Phạm Ngũ Lão, P.1, Q.1, HCM"
  "Tòa nhà Bitexco, 2 Hải Triều, P.Bến Nghé, Q.1, HCM"
  ```

### Yêu cầu
- Không NULL
- Encoding UTF-8 (kiểm tra với `chardet`)
- Độ dài > 5 ký tự (địa chỉ tối thiểu)

---

## ⚙️ PROCESS: Quy trình xử lý

### 1. Model Architecture

**Base Model:** PhoBERT (vinai/phobert-base)
- Pretrained on Vietnamese Wikipedia, Common Crawl
- 12 transformer layers, 768-dim embeddings
- Vocabulary: ~64K subword tokens (SentencePiece)

**Fine-tuning Layer:** Token Classification Head
- Input: Tokenized address (max_length=512)
- Output: BIO tag per token (B-NUM, I-NUM, B-STR, I-STR, ...)
- Loss: CrossEntropyLoss (weighted by class frequency)

### 2. Training Pipeline

**Input Format (Label Studio → BIO):**
```json
{
  "id": 1,
  "text": "268 Lý Thường Kiệt Phường 14",
  "labels": [
    {"value": {"start": 0, "end": 3, "text": "268"}, "normal": "NUM"},
    {"value": {"start": 4, "end": 20, "text": "Lý Thường Kiệt"}, "normal": "STR"},
    {"value": {"start": 21, "end": 30, "text": "Phường 14"}, "normal": "WDS"}
  ]
}
```

**Conversion to BIO Format:**
```
268        → B-NUM
Lý         → B-STR
Thường     → I-STR
Kiệt       → I-STR
Phường     → B-WDS
14         → I-WDS
```

**Data Split:**
- Train: 80% (shuffle with seed=42)
- Validation: 20% (no shuffle, deterministic eval)

**Hyperparameters:**
| Parameter | Default | Range |
|-----------|---------|-------|
| Epochs | 10 | 5-20 |
| Batch Size | 16 | 8-32 (tuỳ GPU memory) |
| Learning Rate | 2e-5 | 1e-5 to 5e-5 |
| Weight Decay | 0.01 | 0.0 to 0.1 |
| Warmup Steps | 100 | 50-500 |

**Training Metrics (HuggingFace Trainer):**
- Loss (CE) per batch
- Validation F1, Precision, Recall (seqeval library)
- Learning rate schedule (linear decay)

**Duration:** ~2h cho 1000 samples (NVIDIA RTX 3090)

### 3. Inference Process

**Input:** Raw address string

**Processing:**
```python
1. Tokenize (PhoBERT tokenizer)
   "268 Lý Thường Kiệt" → ["268", "Ã†", "thÆ°Æ¡ng", "KiÃªt"]
                           (actual SentencePiece tokens)

2. Forward pass (transformer)
   → logits shape: [seq_len, num_labels]

3. Argmax → BIO tags
   ["B-NUM", "B-STR", "I-STR", "I-STR"]

4. Post-process (aggregate subword tokens)
   B-NUM "268"
   B-STR "Lý Thường Kiệt"

5. Format output
   {"NUM": "268", "STR": "Lý Thường Kiệt"}
```

**Batch Inference:**
- max_seq_length: 512 (longer addresses truncated)
- batch_size: 32 (tuỳ GPU memory)
- Padding: Dynamic (pad to max in batch, not 512)

---

## 📤 OUTPUT: Dữ liệu đầu ra

### Format

```python
{
  "NUM": "268",                    # Số nhà
  "STR": "Lý Thường Kiệt",         # Tên đường
  "ALY": None,                     # Hẻm/Ngõ (nếu có)
  "BLD": None,                     # Tòa nhà (nếu có)
  "WDS": "Phường 14",              # Phường/Xã
  "DST": "Quận 10",                # Quận/Huyện
  "PRO": "TP.HCM",                 # Tỉnh/Thành phố
  "NHB": None,                     # Khu phố (nếu có)
  "POI": None,                     # Mốc/Cửa hàng (nếu có)
  "PCD": None                      # Plus Code (nếu có)
}
```

### Lưu trữ

**Model artifacts:**
```
models/phobert-ner-vn/
├── config.json                    # Model config
├── pytorch_model.bin              # Weights
├── tokenizer_config.json          # Tokenizer config
├── tokenizer.json                 # Vocabulary (SPM)
├── vocab.txt                      # Token list
└── training_log.json              # Training metrics
    {
      "final_f1": 0.847,
      "final_precision": 0.863,
      "final_recall": 0.833,
      "epochs": 10,
      "train_samples": 800,
      "eval_samples": 200,
      "timestamp": "2026-05-05T10:30:00Z"
    }
```

**Inference cache:** None (model loaded once at startup)

---

## 🗄️ DATABASE: Liên kết cơ sở dữ liệu

### Đọc (Read)

**Table: `prq.address_cleansing_queue`**
```sql
SELECT id, raw_address, street_address
FROM prq.address_cleansing_queue
WHERE processing_status = 'PENDING'
LIMIT 5000;
```

### Ghi (Write)

**Intermediate storage (in-memory):**
```python
# Không ghi trực tiếp; NER kết quả feed vào Phase 3 (Siamese) & Phase 4 (LLM)
ner_results = ner_model.extract(raw_address)
# Dùng ner_results.get("STR") cho Siamese retrieval
```

**Audit log (optional):**
```sql
INSERT INTO app_logs.ner_inference_log 
  (queue_id, raw_text, entities, confidence, timestamp)
VALUES (...);
```

---

## 🎨 UI/UX: Tích hợp giao diện người dùng

### Address Parser Page
**Vị trí:** `ui/pages/address_parser.html`

**Components:**
1. **Input Box:** Raw address textarea
2. **NER Output Panel:**
   ```
   │ NUM: 268          │
   │ STR: Lý Thường Kiệt │
   │ WDS: Phường 14    │
   │ DST: Quận 10      │
   │ PRO: TP.HCM       │
   ```
3. **Confidence Badge:** Color (green > 0.85, yellow 0.65-0.85, red < 0.65)
4. **Edit/Override buttons:** Cho phép chuỉnh sửa thủ công

### Batch Processing Page
**Vị trí:** `ui/pages/batch_processor.html`

**Display:**
- NER extraction log (realtime)
- Success / Failure rate
- Retry failed records

---

## 📊 METRICS & EVALUATION

### Training Metrics

**Token-level (Micro-averaged):**
| Metric | F1 | Precision | Recall |
|--------|----|-----------
|--------|
| NUM | 0.92 | 0.94 | 0.90 |
| STR | 0.88 | 0.89 | 0.87 |
| WDS | 0.85 | 0.86 | 0.84 |
| DST | 0.87 | 0.88 | 0.86 |
| PRO | 0.90 | 0.92 | 0.88 |
| ALY | 0.78 | 0.80 | 0.76 |
| BLD | 0.72 | 0.74 | 0.70 |
| **Overall** | **0.847** | **0.863** | **0.833** |

**Sanity Check:**
```bash
python app/ai/train_ner.py --data data/ner_samples_20260425_1000_prelabeled.json --validate-only
```

### Error Analysis

**Top confusion pairs:**
1. WDS vs ALY (Phường vs Hẻm: context-dependent)
2. STR vs NHB (Tên đường vs Khu phố: abbrev overlap)
3. BLD confidence (short phrases, high variation)

---

## ✅ VALIDATION & GUARDRAILS

### Data Validation

- [ ] Label Studio JSON valid (check with `label_studio_sdk`)
- [ ] All tokens have labels (no unlabeled gaps)
- [ ] BIO consistency (I-X must follow B-X)
- [ ] No overlapping spans

### Model Validation

```python
# Kiểm tra
assert len(tokenizer.vocab) >= 60000  # PhoBERT vocab size
assert model.num_labels == 21          # "O" + 10 labels × 2 (B, I)
assert model.config.max_position_embeddings >= 512
```

### Output Validation

```python
# Kiểm tra output
ner_out = ner_model.extract(address)
assert isinstance(ner_out, dict)
assert all(k in NER_LABELS_LIST for k in ner_out.keys())
assert all(isinstance(v, str) or v is None for v in ner_out.values())
```

---

## 🔧 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Low F1 on WDS/DST | Label imbalance | Use class weights in loss |
| OOM during training | Batch size too large | Reduce to 8-16 |
| Tokenizer mismatch | Different vocab | Use same tokenizer from model config |
| Inference slow (>100ms) | CPU inference | Use GPU (device=0) |

---

## 📚 References

- **Code:** `app/ai/models/ner_model.py`, `app/ai/train_ner.py`
- **Config:** `app/ai/constants.py` (`NER_LABELS`: dict/object per entity with `value`, `color`, `hotkey` — không có `text`; Label Studio dùng `value` làm nhãn hiển thị). **UI:** `GET /api/config/ner-labels` → `{ "labels": [ ... ] }`.
- **Labels:** 10 entity types defined in `constants.py`
- **Training script:** `app/ai/train_ner.py`

---

**Version:** 1.0  
**Status:** Production  
**Last Updated:** 2026-05-05  
**Next Tuning:** Post-deployment (2026-06-05)
