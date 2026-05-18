# Google Colab Integration - Complete Package

## 📦 Files Created

```
scripts/colab/
├── README.md                          # Tổng quan workflow
├── QUICKSTART.md                      # Hướng dẫn nhanh
├── export_ground_truth_sqlite.py      # Export PostgreSQL → SQLite
├── export_noise_profiles.py           # Export noise profiles → JSON
├── import_colab_results.py            # Import CSV → PostgreSQL
└── vnai_ablation_study.ipynb          # Colab notebook (8 cells)
```

---

## 🚀 Workflow 3 Phase

### **Phase 1: Chuẩn bị (Local, ~5 phút)**

```bash
cd "d:\2.GIT SOURCE\vn-address-intelligence"

# Export data
python scripts/colab/export_ground_truth_sqlite.py --limit 15000 --output ground_truth.db
python scripts/colab/export_noise_profiles.py --output noise_profiles.json

# Verify
ls -lh ground_truth.db noise_profiles.json
```

**Upload lên Google Drive:**
- Tạo folder `My Drive/colab_vnai/`
- Upload: `ground_truth.db`, `noise_profiles.json`, `vnai_ablation_study.ipynb`

---

### **Phase 2: Chạy Colab (GPU T4, ~2–3 giờ)**

1. Mở https://colab.research.google.com/
2. File → Upload notebook → chọn `vnai_ablation_study.ipynb`
3. Runtime → Change runtime type → **GPU (T4)**
4. Chạy từng cell (1→8)
5. Download `ablation_n1000_results.csv` ở cell 8

**Timeline:**
- Cell 1 (Setup): ~5 phút
- Cell 2 (Load models): ~10 phút (download Qwen, mGTE, PhoBERT)
- Cell 3 (Extract cohort): ~1 phút
- Cell 4 (A1 Full): ~30 phút
- Cell 5 (A2 NER+mGTE): ~20 phút
- Cell 6 (A3 mGTE): ~20 phút
- Cell 7 (A4 NER+LLM): ~25 phút
- Cell 8 (Export): ~1 phút
- **Tổng: ~2–3 giờ**

---

### **Phase 3: Import & Eval (Local, ~15 phút)**

```bash
# Import CSV
python scripts/colab/import_colab_results.py --csv ablation_n1000_results.csv

# Output sẽ in ra các run_id (ví dụ 101–104)
# Chạy eval cho từng run:
python scripts/experiments/supa_benchmark.py eval --run-id 101
python scripts/experiments/supa_benchmark.py eval --run-id 102
python scripts/experiments/supa_benchmark.py eval --run-id 103
python scripts/experiments/supa_benchmark.py eval --run-id 104

# Aggregate
python scripts/experiments/supa_benchmark.py aggregate-runs \
    --run-ids 101,102,103,104 \
    --out-json reports/ablation_n1000_colab_aggregate.json

# Xem kết quả
cat reports/ablation_n1000_colab_aggregate.json
```

---

## 📊 Kết quả mong đợi

### CSV Structure
```csv
gt_id,raw_address,ref_address_v2,pred_standardized,latency_ms,config
1,Số 10 Nguyễn Huệ...,Số 10 Nguyễn Huệ...,Số 10 Nguyễn Huệ...,1234.5,A1_FULL
2,...,...,...,...,A1_FULL
...
1001,...,...,...,...,A2_NER_MGTE
...
```

### Aggregate JSON
```json
{
  "runs": [
    {
      "run_id": 101,
      "config": "A1_FULL",
      "n": 1000,
      "em_v2": 0.XX,
      "mean_latency_ms": XXX.X,
      "p95_latency_ms": XXX.X
    },
    ...
  ],
  "summary": {
    "total_runs": 4,
    "total_specimens": 4000,
    "best_em_v2": {...}
  }
}
```

---

## 🔧 Troubleshooting

### ❌ Colab: "Runtime disconnected"
**Nguyên nhân:** Session timeout (12h free tier)

**Giải pháp:**
- Chạy từng config riêng (4 session × 30 phút)
- Hoặc nâng cấp Colab Pro (24h session)

---

### ❌ Colab: "Out of memory"
**Nguyên nhân:** GPU RAM không đủ (T4 = 15GB)

**Giải pháp:**
```python
# Trong cell 2, giảm corpus_limit
retriever = SiameseMGTE(corpus_limit=8000, device="cuda")  # thay vì 12000
```

---

### ❌ Import: "run_id already exists"
**Nguyên nhân:** Đã import CSV này rồi

**Giải pháp:**
```sql
-- Xóa run cũ
DELETE FROM prq.supa_benchmark_specimen WHERE run_id IN (101, 102, 103, 104);
DELETE FROM prq.supa_benchmark_run WHERE id IN (101, 102, 103, 104);
```

---

### ❌ Eval: "No specimens found"
**Nguyên nhân:** Import chưa xong hoặc run_id sai

**Giải pháp:**
```sql
-- Kiểm tra
SELECT run_id, COUNT(*) FROM prq.supa_benchmark_specimen GROUP BY run_id;
```

---

## 📈 So sánh CPU vs Colab

| Metric | CPU Local (N=50) | Colab GPU (N=1000) | Cải thiện |
|--------|------------------|---------------------|-----------|
| **Cohort size** | 50 | 1000 | **20×** |
| **Cấu hình** | 3 (không LLM) | 4–5 (có LLM) | **+33%** |
| **Thời gian** | ~6 giờ | ~2–3 giờ | **2–3×** |
| **LLM** | ❌ Không chạy được | ✅ Chạy được | ✅ |
| **EM tin cậy** | ❌ N quá nhỏ | ✅ Đủ lớn | ✅ |
| **Chi phí** | $0 | $0 (free tier) | — |

---

## 📝 Next Steps

Sau khi có `ablation_n1000_colab_aggregate.json`:

1. **Cập nhật báo cáo** `docs/scientific-report/VNAI-he-thong-thuc-hien-tong-hop.md`:
   - Mục 9.10.1: Bảng kết quả Ablation N=1000
   - Mục 10.0: Kết luận có LLM
   - Mục 10.4: Bỏ hạn chế "không đánh giá LLM"

2. **Chạy Stratified K=5** (N=2000×5, pipeline thật):
   ```bash
   python scripts/experiments/supa_benchmark.py replicate-stratified --k-runs 5 --n 2000
   # Rồi chạy pipeline cho từng run_id
   ```

3. **SUPA Final** (N=10,000) nếu thời gian cho phép

---

## 📚 References

- Colab notebook: `scripts/colab/vnai_ablation_study.ipynb`
- Export scripts: `scripts/colab/export_*.py`
- Import script: `scripts/colab/import_colab_results.py`
- SUPA-Bench docs: `docs/scientific-report/SUPA-BENCH-RUNBOOK.md`
