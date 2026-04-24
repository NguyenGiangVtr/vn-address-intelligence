# 🇻🇳 VN Address Intelligence

> **Framework học sâu để chuẩn hóa và làm sạch địa chỉ Việt Nam phi cấu trúc**, kết hợp PhoBERT, Siamese Network và LLM trong một pipeline thực nghiệm có thể kết nối trực tiếp PostgreSQL.

---

## 📋 Tổng quan

Địa chỉ Việt Nam trong thực tế thường bị viết tắt, sai chính tả, thiếu tầng hành chính hoặc không theo chuẩn 4 tầng *(Số nhà + Đường → Phường/Xã → Quận/Huyện → Tỉnh/Thành phố)*. Dự án này cung cấp:

1. **Hệ thống Ensemble 4 tầng** chạy trên Google Colab (GPU) — độ chính xác cao, latency thấp.
2. **Framework thực nghiệm** so sánh 3 kiến trúc cốt lõi để tìm mô hình tối ưu nhất cho production.
3. **Tích hợp PostgreSQL** — đọc data thô, chuẩn hóa, ghi kết quả trở lại DB vào các cột mới.

---

## 🏗️ Kiến trúc Hệ thống

### Pipeline Ensemble 4 Tầng (`colab_ensemble_address.py`)

```
Input: "123 Ng Huệ, Bến Nghé, Q1, HCM"
        ↓
┌────────────────────────────────────────┐
│ Tầng 1: ColBERTv2 — Candidate Gen     │  → 500 ứng viên  | ~45ms
│   Token-level MaxSim late interaction  │
└────────────────────┬───────────────────┘
                     ↓
┌────────────────────────────────────────┐
│ Tầng 2: mGTE Dense Retriever          │  → 20 ứng viên   | ~35ms
│   Cosine similarity (1024-dim vectors) │
└────────────────────┬───────────────────┘
                     ↓
┌────────────────────────────────────────┐
│ Tầng 3: Cross-Encoder Precision       │  → 3 ứng viên    | ~55ms
│   Joint encoding (query + candidate)  │
└────────────────────┬───────────────────┘
                     ↓
          [Confidence < 0.7?]
          ↙ Không          ↘ Có
     Return              Tầng 4: Qwen3 LLM
     Result              Fallback ~1000ms+

Output: "123 Đường Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh"
```

### Framework Thực Nghiệm (`experiment_runner.py`)

So sánh 3 kiến trúc cốt lõi trên dữ liệu thực từ PostgreSQL:

| Mô hình | Backbone | Vai trò | Ghi chú |
|---|---|---|---|
| **PhoBERT Siamese** | `vinai/phobert-base` | Bi-Encoder tiếng Việt | Cần tách từ (PyVi) |
| **mGTE Siamese** | `Alibaba-NLP/gte-multilingual-base` | Baseline đa ngôn ngữ | Zero-shot, không cần fine-tune |
| **LLM Qwen3** | `Qwen/Qwen3-4B` | Reasoner / Fallback | Dùng top-5 từ mGTE làm candidates |

---

## 📁 Cấu trúc Dự án

```
vn-address-intelligence/
├── README.md
├── requirements.txt
│
├── docs/
│   ├── colab_guide.md                   # Hướng dẫn chạy trên Google Colab
│   └── quick_reference.md               # Cheatsheet code snippets & config
│
└── src/
    ├── colab_ensemble_address.py        # Pipeline Ensemble 4 tầng (Colab)
    ├── config.yaml                      # Cấu hình DB, models, experiment
    ├── db_connector.py                  # PostgreSQL: đọc/ghi dữ liệu
    ├── experiment_runner.py             # ← Entry-point thực nghiệm
    ├── metrics.py                       # Exact Match, Levenshtein, Component Acc
    ├── report_generator.py              # Báo cáo HTML + CSV
    ├── find_schema.py                   # Tiện ích khám phá schema DB
    └── models/
        ├── __init__.py
        ├── phobert_model.py             # PhoBERT Siamese Bi-Encoder
        ├── siamese_mgte.py              # mGTE Siamese (baseline)
        └── llm_model.py                 # Qwen3 LLM zero-shot
```

---

## 🚀 Hướng dẫn Sử dụng

### Option A — Google Colab (Ensemble 4 tầng)

1. Mở [Google Colab](https://colab.research.google.com), bật **GPU (T4/L4)**
2. Copy toàn bộ `src/colab_ensemble_address.py` vào notebook
3. Chạy tuần tự từ **CELL 0 → CELL 14**
4. Xem hướng dẫn chi tiết tại [`docs/colab_guide.md`](docs/colab_guide.md)

> ⏱️ Lần đầu tải models: ~10–15 GB, mất 3–5 phút

### Option B — Thực nghiệm với PostgreSQL

**Bước 1: Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

**Bước 2: Cấu hình kết nối DB**

Chỉnh file `src/config.yaml`:
```yaml
database:
  host: "your-db-host"
  port: 5432
  dbname: "your_database"
  user: "your_user"
  password: "your_password"
  schema: "your_schema"        # VD: "scm", "public"
  table_name: "your_table"
  id_column: "id"              # Cột Primary Key
  input_column: "address_col"  # Cột chứa địa chỉ thô
  limit: 1000                  # Số dòng lấy để thực nghiệm
```

**Bước 3: Khám phá schema (nếu chưa biết)**
```bash
python src/find_schema.py
```

**Bước 4: Chạy thực nghiệm**
```bash
# Chạy PhoBERT + mGTE (không cần GPU lớn)
python src/experiment_runner.py --config src/config.yaml --no-llm

# Chạy đầy đủ cả 3 mô hình (cần GPU 8GB+)
python src/experiment_runner.py --config src/config.yaml
```

**Kết quả:**
- Cột mới `normalized_phobert`, `normalized_mgte`, `normalized_llm` được ghi vào DB
- Báo cáo HTML: `reports/experiment_report.html`
- CSV: `reports/experiment_results.csv`

---

## 📊 Chỉ số Đánh giá

| Metric | Mô tả |
|---|---|
| **Exact Match** | % địa chỉ khớp hoàn toàn với ground truth |
| **Fuzzy Match** | % địa chỉ có Levenshtein ≥ 0.85 |
| **Levenshtein Score** | Điểm tương đồng chuỗi trung bình (0–1) |
| **Phường Accuracy** | Độ chính xác thành phần Phường/Xã |
| **Quận Accuracy** | Độ chính xác thành phần Quận/Huyện |
| **Tỉnh/TP Accuracy** | Độ chính xác thành phần Tỉnh/Thành phố |
| **Latency P95 (ms)** | Thời gian xử lý percentile 95 |
| **Throughput (qps)** | Số query xử lý được trong 1 giây |

### Benchmark Kỳ vọng (Pipeline Ensemble 4 tầng)

| Layer | Latency | Accuracy |
|---|---|---|
| Tầng 1 (ColBERT) | 40–60ms | — |
| Tầng 2 (mGTE) | 30–50ms | — |
| Tầng 3 (Cross-Encoder) | 50–100ms | Exact Match ~92% |
| Tầng 4 (LLM, nếu trigger) | 500–2000ms | Fuzzy Match ~97% |
| **Tổng (không LLM)** | **~120–210ms** | **Coverage ~99%** |

---

## ⚙️ Cấu hình Nâng cao

### Chế độ chạy

```yaml
# Nhanh — Production (không LLM)
experiment:
  corpus_limit: 50000        # Giới hạn corpus để thực nghiệm nhanh

# Chính xác cao — Research
models:
  phobert:
    enabled: true
  llm:
    enabled: true
    use_quantization: true   # 8-bit quantization tiết kiệm VRAM
```

### Xử lý Primary Key
Dự án yêu cầu bảng có cột Primary Key (mặc định là `id`) để cập nhật kết quả chuẩn hóa. Nếu bảng của bạn sử dụng tên cột khác, hãy khai báo trong `id_column` của file config. `db_connector.py` sẽ ưu tiên sử dụng cột này để đồng bộ dữ liệu.

---

## 🔧 Yêu cầu Hệ thống

| Thành phần | Yêu cầu tối thiểu |
|---|---|
| Python | 3.9+ |
| GPU VRAM | 8GB (T4) — để chạy LLM |
| RAM | 16GB |
| Disk | 20GB (cho models) |
| PostgreSQL | 12+ |

---

## 📦 Models Sử dụng

| Tầng | Model | HuggingFace Hub |
|---|---|---|
| Tầng 1 | ColBERTv2 | `colbert-ir/colbertv2.0` |
| Tầng 2 | mGTE Multilingual | `Alibaba-NLP/gte-multilingual-base` |
| Tầng 3 | Cross-Encoder | `cross-encoder/multilingual-MiniLMv2-L12-H384-uncased` |
| Tầng 4 | Qwen3-4B | `Qwen/Qwen3-4B` |
| Thực nghiệm | PhoBERT | `vinai/phobert-base` |

---

## 📚 Tài liệu Tham khảo

- [ColBERTv2 Paper](https://arxiv.org/abs/2112.01488)
- [mGTE Paper](https://arxiv.org/abs/2407.19669)
- [PhoBERT (VinAI)](https://github.com/VinAIResearch/PhoBERT)
- [Qwen3 Blog](https://qwenlm.github.io/blog/qwen3/)
- [Sentence Transformers](https://www.sbert.net/)

---

## 📝 Ghi chú

- **Lần đầu chạy:** Tải models từ HuggingFace (~10–15GB), mất 3–5 phút
- **Windows:** `bitsandbytes` (quantization) chỉ hỗ trợ đầy đủ trên Linux/CUDA. Trên Windows đặt `use_quantization: false`
- **PyVi warning:** Cảnh báo NumPy deprecation từ `pyvi` là vô hại, không ảnh hưởng kết quả

---

*Version 1.0 — April 2026*
