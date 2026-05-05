# 🔄 VNAI Training Pipeline - Complete System Overview

**Cập nhật: 2026-05-05**  
**Phạm vi:** Toàn bộ quy trình huấn luyện (Training), thử nghiệm (Experiment) và sử dụng thực tiễn (Inference)  
**Mục tiêu:** Chuẩn hóa và làm giàu địa chỉ Việt Nam theo bối cảnh cải cách hành chính 2025

---

## 📊 Tổng quan: 5 Thành phần chính

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VNAI Training & Inference Pipeline               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Database (Ground Truth)                                           │
│    ↓                                                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  PHASE 1: Data Preparation & Pre-Labeling               │   │
│  │  • Export from Queue + Join Administrative Context       │   │
│  │  • PreLabeler: Regex + Master Data (Hybrid)            │   │
│  │  • Output: Label Studio JSON (Semi-labeled)            │   │
│  └────────────────────────────────────────────────────────────┘   │
│    ↓                                                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  PHASE 2: NER Model Training & Validation              │   │
│  │  • Load & Curate Label Studio JSON                      │   │
│  │  • Fine-tune PhoBERT (Transformer-based NER)           │   │
│  │  • Metrics: F1, Precision, Recall (seqeval)           │   │
│  │  • Save: models/phobert-ner-vn/                        │   │
│  └────────────────────────────────────────────────────────────┘   │
│    ↓                                                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  PHASE 3: Retrieval Model Training (Siamese)            │   │
│  │  • PhoBERT Siamese (Dense Retriever - Optional)        │   │
│  │  • mGTE Siamese (Multilingual Baseline)                │   │
│  │  • Build Corpus Embeddings + Index                     │   │
│  │  • Metrics: MRR, NDCG, Top-K Accuracy                 │   │
│  └────────────────────────────────────────────────────────────┘   │
│    ↓                                                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  PHASE 4: LLM Fine-tuning / Prompt Engineering        │   │
│  │  • Qwen 2.5 LLM (Zero-shot / In-context Learning)     │   │
│  │  • Prompt: Query + Top-5 Candidates → Normalized JSON │   │
│  │  • Metrics: Exact Match, Fuzzy Match, Structure        │   │
│  └────────────────────────────────────────────────────────────┘   │
│    ↓                                                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  PHASE 5: Integration & Production Inference           │   │
│  │  • Pipeline: NER → Dictionary + Siamese → LLM         │   │
│  │  • Batch Processing (address_cleansing_queue)          │   │
│  │  • Confidence Scoring (F1-weighted ensemble)           │   │
│  │  • Output: address_standardized (Database Update)      │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Chi tiết từng Phase

### **PHASE 1: Data Preparation & PreLabeling**

**Thành phần:** `PreLabeler` ([02_PreLabeler.md](02_PreLabeler.md))

| Yếu tố | Chi tiết |
|--------|---------|
| **Mục đích** | Tự động gợi ý nhãn (semi-annotation) để giảm công sức curation |
| **Input** | Raw address từ `prq.address_cleansing_queue` + Administrative context (ward, district, province) |
| **Process** | Hybrid Labeling: String Matching (Master Data) + Regex (Heuristics) |
| **Output** | `data/ner_samples_<timestamp>_prelabeled.json` (Label Studio format) |
| **Database** | Đọc từ: `prq.address_cleansing_queue`, `mat.ward`, `mat.district`, `mat.province` |
| **UI/UX** | Label Studio Web Editor (quản lý & cải chính nhãn) |
| **Kiểm chứng** | - Không thiếu nhãn bắt buộc (NUM, STR) <br> - Consistency: không trùng lặp token <br> - Confidence > 0.5 |

**Lệnh chạy:**
```bash
python app/ai/export_for_annotation.py --limit 1000 --config app/ai/config.yaml
```

---

### **PHASE 2: NER Model Training**

**Thành phần:** `AddressNER` ([01_NER_Entities.md](01_NER_Entities.md))

| Yếu tố | Chi tiết |
|--------|---------|
| **Mục đích** | Bóc tách thành phần địa chỉ (Số nhà, Tên đường, Tòa nhà, Hẻm...) từ văn bản thô |
| **Input** | Label Studio JSON (manual curated annotations) |
| **Model Base** | PhoBERT (vinai/phobert-base) - Vietnamese BERT |
| **Process** | 1. Convert to BIO format 2. Fine-tune w/ HuggingFace Trainer 3. Evaluate w/ seqeval |
| **Output** | `models/phobert-ner-vn/` (model + tokenizer + training_log.json) |
| **Nhãn (Tags)** | 10 nhãn NER: NUM, STR, NHB, ALY, WDS, DST, BLD, POI, PRO, PCD (xem `constants.py`) |
| **Database** | Không trực tiếp; dùng output cho Phase 3 & 5 |
| **UI/UX** | Label Studio (annotation), Dashboard (metrics visualization) |
| **Metrics** | F1, Precision, Recall (token-level), seqeval library |
| **Kiểm chứng** | BIO format validation, label consistency, F1 > 0.75 (target) |

**Lệnh chạy:**
```bash
python app/ai/train_ner.py --data data/ner_samples_20260425_1000_prelabeled.json \
  --output models/phobert-ner-vn --epochs 10 --batch-size 16
```

---

### **PHASE 3: Retrieval Model Training (Siamese)**

**Thành phần:** `PhoBERTSiamese`, `SiameseMGTE` ([03_PhoBERT_Siamese.md](03_PhoBERT_Siamese.md), [04_mGTE_Siamese.md](04_mGTE_Siamese.md))

| Yếu tố | Chi tiết |
|--------|---------|
| **Mục đích** | Tìm địa chỉ chuẩn (normalized) gần nhất cho một query thô |
| **Input** | Corpus: `prq.address_clean_corpus` (hoặc cached embeddings) |
| **Model Base** | **mGTE** (Alibaba-NLP/gte-multilingual-base) - Zero-shot <br> **PhoBERT** (vinai/phobert-base) - Optional fine-tune |
| **Process** | 1. Encode query → dense vector 2. Cosine similarity vs corpus embeddings 3. Top-K retrieval |
| **Output** | - Corpus embeddings (numpy array, serialized) <br> - Retrieval index (FAISS optional) <br> - Top-5 candidates per query |
| **Database** | Đọc corpus từ: `prq.address_clean_corpus` (hoặc materialized view) |
| **UI/UX** | Lookup page (hiển thị top candidates) |
| **Metrics** | MRR (Mean Reciprocal Rank), NDCG, Top-1/Top-5 accuracy |
| **Kiểm chứng** | Corpus size ≥ 100K addresses, embeddings dimension = 768/384 |

**Lệnh chạy (mGTE):**
```bash
python app/ai/models/siamese_mgte.py encode_corpus --corpus prq.address_clean_corpus --output models/mgte-corpus.npy
```

---

### **PHASE 4: LLM Fine-tuning / Prompt Engineering**

**Thành phần:** `LLMQwen3` ([05_Qwen_LLM.md](05_Qwen_LLM.md))

| Yếu tố | Chi tiết |
|--------|---------|
| **Mục đích** | Suy luận ngữ cảnh & chuẩn hóa địa chỉ thành cấu trúc JSON (Zero-shot LLM) |
| **Input** | Query (from NER) + Top-5 candidates (from Siamese) |
| **Model** | Qwen 2.5 (4B hoặc 14B) - Quantized 8-bit |
| **Process** | Prompt engineering: [Instruction] + [Query] + [Candidates] → JSON |
| **Output** | Normalized address JSON: street_number, route, level_3, level_2, level_1, postal_code |
| **Database** | Không trực tiếp; intermediate input từ Phase 3 |
| **UI/UX** | Parser page (hiển thị JSON components) |
| **Metrics** | Exact Match (street_number, route), Fuzzy Match (routing), Structure validity |
| **Kiểm chứng** | JSON valid, bắt buộc fields (route, level_3, level_1), confidence > 0.6 |

**Lệnh chạy (Inference):**
```bash
# Integrated vào production_pipeline.py
python -m app.ai.production_pipeline --limit 5000 --config app/ai/config.yaml
```

---

### **PHASE 5: Production Inference & Integration**

**Thành phần:** `production_pipeline.py` (Orchestrator)

| Yếu tố | Chi tiết |
|--------|---------|
| **Mục đích** | Xử lý batch từ queue, chuẩn hóa & lưu kết quả |
| **Input** | `prq.address_cleansing_queue` (PENDING records) |
| **Orchestration** | 1. NER Extract 2. Dictionary Normalize 3. Siamese Retrieve 4. LLM Process 5. Confidence Score 6. Save |
| **Output** | `prq.address_cleansing_queue` cập nhật: `address_standardized`, `processing_method`, `confidence_score` |
| **Database** | Đọc: queue, corpus; Ghi: queue (results) |
| **Performance** | Throughput ≥ 100 records/min (target), latency < 2s/record |
| **Kiểm chứng** | No NULL in mandatory fields, confidence within [0, 1], processing_status = 'COMPLETED' |

---

## 📈 Training vs Inference Workflow

### **Training Workflow** (Offline, Development)

```
1. Export từ DB + PreLabel (PreLabeler)
   ↓
2. Curate & Annotate trên Label Studio (Human in the Loop)
   ↓
3. Train NER (PhoBERT)
   ↓
4. Train/Eval Siamese (mGTE or PhoBERT)
   ↓
5. Run Experiment (A/B test on holdout set)
   ↓
6. Generate Report & Metrics
   ↓
7. Deploy best model → models/
```

**Duration:** 2-4 giờ (tuỳ dataset size & hardware)

### **Inference Workflow** (Online, Production)

```
Input: address_cleansing_queue (PENDING)
   ↓
Phase 1 (NER): Extract entities
   ↓
Phase 2 (Dictionary): Normalize abbreviations
   ↓
Phase 3 (Siamese): Retrieve top-5 candidates
   ↓
Phase 4 (LLM): Select best + fill structure
   ↓
Phase 5 (Score & Save): Confidence + Update DB
   ↓
Output: address_standardized
```

**Throughput:** Tuỳ batch size (typical: 100-5000 records/batch)

---

## ✅ Kiểm chứng & Validation

### **Level 1: Data Quality**
- [ ] No NULLs in raw_address, street_address
- [ ] Addressing components consistency (ward ∈ district, etc.)
- [ ] Encoding consistency (UTF-8)

### **Level 2: Model-specific**
- [ ] NER: F1 > 0.75 on validation set
- [ ] Siamese: Top-1 MRR > 0.7 (exact match)
- [ ] LLM: JSON structure valid, mandatory fields present

### **Level 3: Integration**
- [ ] Pipeline latency < 2s/record
- [ ] Confidence score distribution (should be narrow if well-calibrated)
- [ ] Failure rate < 2% (no exceptions during batch)

### **Level 4: Business Logic**
- [ ] address_standardized matches expected format
- [ ] processing_method logged correctly
- [ ] Audit trail (who, when, what) recorded

---

## 📊 KPI & Reporting

### **Training KPI**
| Metric | Target | Baseline | Unit |
|--------|--------|----------|------|
| NER F1 (Token-level) | > 0.85 | 0.75 | % |
| Siamese Top-1 Accuracy | > 0.80 | 0.65 | % |
| LLM Exact Match (routing) | > 0.75 | 0.60 | % |
| Data Prep Time | < 2h | 4h | hours |

### **Production KPI**
| Metric | Target | Unit |
|--------|--------|------|
| Throughput | ≥ 100 records/min | records/min |
| Latency (p95) | < 2s | seconds |
| Success Rate | > 98% | % |
| Confidence Score (μ) | > 0.70 | score [0,1] |

---

## 🔍 References to Detailed Docs

- **01_NER_Entities.md** - PhoBERT NER model details
- **02_PreLabeler.md** - Hybrid labeling strategy
- **03_PhoBERT_Siamese.md** - Dense retriever (Vietnamese optimized)
- **04_mGTE_Siamese.md** - Multilingual zero-shot baseline
- **05_Qwen_LLM.md** - LLM inference & prompt engineering
- **ai-training-workflow-summary.md** - Legacy workflow reference
- **[database.md](../02-database/database.md)** - Schema & queries

---

**Version:** 1.0  
**Last Updated:** 2026-05-05  
**Next Review:** 2026-06-05 (Post-deployment tuning)
