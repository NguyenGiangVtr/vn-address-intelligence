# 📊 Tìm thấy các File Metrics và Artifacts

**Ngày:** 2026-05-17  
**Thời gian:** 19:15 (UTC+7)

---

## ✅ Tất cả các file đã tìm thấy

### 1. **Metrics TEX Files (LaTeX)**

#### 📄 `vnai-generated-metrics.tex`
- **Location:** `docs\scientific-report\mis-DATN-2026\metrics\vnai-generated-metrics.tex`
- **Size:** 5.4 KB (109 dòng)
- **Generated:** 2026-05-12T04:46:58Z
- **Content:**
  - NER metrics (F1: 93.76%, Precision: 92.90%, Recall: 94.64%)
  - Audit metrics (G2: 96.61%, G3: 96.79%)
  - **Ablation Study metrics** (mới thêm 2026-05-17):
    - 5 cấu hình (A1-A4)
    - 25,000 specimens total
    - Platform: Google Colab GPU T4
    - Git commit: 4daf4042

#### 📄 `vnai-supa-generated-metrics.tex`
- **Location:** `docs\scientific-report\mis-DATN-2026\metrics\vnai-supa-generated-metrics.tex`
- **Size:** 711 bytes (17 dòng)
- **Generated:** 2026-05-12T07:32:13Z
- **Content:**
  - SUPA run_id: 1
  - N: 1000 specimens
  - EM@v2: 100% (oracle demo)
  - EM@v1: 3.5%
  - Noise profile: SUP-1.0.0

---

### 2. **Ablation Aggregate JSON**

#### 📄 `ablation_n1000_colab_aggregate.json`
- **Location:** `reports\ablation_n1000_colab_aggregate.json`
- **Size:** 3.8 KB (155 dòng)
- **Generated:** 2026-05-17T06:26:52Z
- **Git commit:** 4daf4042

**Dữ liệu:**
- **Runs:** 100-104 (5 runs)
- **N per run:** 5,000 specimens
- **Total:** 25,000 specimens
- **Noise profile:** SUP-1.0.0

**Metrics (rollup mean):**
- EM@v2: 51.60% (±24.24%, range: 8.46%-66.58%)
- F1 Street: 74.95% (±11.33%)
- F1 Ward: 82.14% (±35.66%)
- F1 District: 99.04% (±0.58%)
- F1 Province: 81.28% (±6.76%)

**Per-config results:**
- **A1_FULL** (run 100): EM@v2 66.58%, NER+mGTE+LLM
- **A2_NER_TFIDF** (run 101): EM@v2 60.98%, NER+TF-IDF
- **A2_NER_MGTE** (run 102): EM@v2 60.98%, NER+mGTE
- **A3_MGTE_ONLY** (run 103): EM@v2 60.98%, retrieval-only
- **A4_NER_LLM** (run 104): EM@v2 8.46%, NER+LLM (no retrieval)

---

### 3. **SUPA Stratified K=5 Aggregate JSON**

#### 📄 `supa_benchmark_aggregate_stratified_final.json`
- **Location:** `reports\supa_benchmark_aggregate_stratified_final.json`
- **Size:** 3.8 KB (155 dòng)
- **Generated:** 2026-05-16T05:35:52Z
- **Git commit:** 24a45cdd

**Dữ liệu:**
- **Runs:** 82-86 (5 runs) ⚠️ **Không phải 56-60**
- **N per run:** 2,000 specimens
- **Total:** 10,000 specimens
- **Noise profile:** STRATIFIED-strat-v1

**Metrics (rollup mean):**
- EM@v2: 100.0% (±0.0%) - **Oracle mode**
- EM@v1: 14.31% (±0.56%, range: 13.4%-14.8%)
- F1 Street: 100.0%
- F1 Ward: 100.0%
- F1 District: 100.0%
- F1 Province: 100.0%
- **Latency mean:** 2.49ms (±0.09ms)
- **Latency P95:** 2.80ms (±0.12ms)
- **Throughput:** 402.13 addr/s (±13.55)

---

## 📝 Lưu ý quan trọng

### ⚠️ File không tìm thấy
Bạn yêu cầu file: `supa_benchmark_aggregate_stratified_k5_oracle_run56-60_20260513.json`

**Không tìm thấy file này.** Thay vào đó, tìm thấy:
- `supa_benchmark_aggregate_stratified_final.json` (runs 82-86, ngày 2026-05-16)

**Có thể:**
1. File run 56-60 đã bị xóa hoặc đổi tên
2. File run 82-86 là phiên bản mới nhất thay thế run 56-60
3. File run 56-60 có thể trong archive

---

## 🎯 Sử dụng trong LaTeX

Các file `.tex` trong `metrics/` đã được tự động sinh và có thể include trực tiếp:

```latex
\input{metrics/vnai-generated-metrics.tex}
\input{metrics/vnai-supa-generated-metrics.tex}
```

**Macros có sẵn:**
- `\VNAIGENNERFOnePct` → 93.76
- `\VNAIABLATIONAOneEMvTwoPct` → 66.58
- `\VNASUPAEMvTwoPct` → 100.0000
- ... và nhiều macros khác

---

## 📂 Đường dẫn đầy đủ

```
D:\2.GIT SOURCE\vn-address-intelligence\
├── docs\scientific-report\mis-DATN-2026\metrics\
│   ├── vnai-generated-metrics.tex
│   └── vnai-supa-generated-metrics.tex
│
└── reports\
    ├── ablation_n1000_colab_aggregate.json
    └── supa_benchmark_aggregate_stratified_final.json
```

---

**Tìm kiếm hoàn tất:** 2026-05-17 19:15 (UTC+7)
