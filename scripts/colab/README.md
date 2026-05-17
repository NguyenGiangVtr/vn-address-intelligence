# Google Colab Integration Scripts

Scripts để chạy thực nghiệm SUPA-Bench trên Google Colab với GPU.

## Workflow

### Phase 1: Chuẩn bị dữ liệu (local)

```bash
# 1. Export ground_truth sang SQLite
python scripts/colab/export_ground_truth_sqlite.py --limit 15000 --output ground_truth.db

# 2. Export noise profiles
python scripts/colab/export_noise_profiles.py --output noise_profiles.json

# 3. Upload lên Google Drive:
#    - ground_truth.db
#    - noise_profiles.json
#    - Colab notebook (vnai_ablation_study.ipynb)
```

### Phase 2: Chạy trên Colab

Mở `vnai_ablation_study.ipynb` trên Google Colab và chạy từng cell.

**Thời gian ước tính (GPU T4):**
- A1 (NER + mGTE + LLM): ~30 phút
- A2 (NER + mGTE): ~20 phút
- A3 (mGTE only): ~20 phút
- A4 (NER + LLM): ~25 phút
- A5 (NER + PhoBERT + LLM): ~30 phút
- **Tổng: ~2–3 giờ**

### Phase 3: Import kết quả về PostgreSQL

```bash
# Download CSV từ Colab
# Rồi import:
python scripts/colab/import_colab_results.py --csv ablation_n1000_results.csv

# Chạy eval cho từng run_id (xem output của import script)
python scripts/experiments/supa_benchmark.py eval --run-id 101
python scripts/experiments/supa_benchmark.py eval --run-id 102
# ...

# Aggregate
python scripts/experiments/supa_benchmark.py aggregate-runs \
    --run-ids 101,102,103,104,105 \
    --out-json reports/ablation_n1000_colab_aggregate.json
```

## Files

- `export_ground_truth_sqlite.py` — Export PostgreSQL → SQLite
- `export_noise_profiles.py` — Export noise profiles → JSON
- `import_colab_results.py` — Import CSV từ Colab → PostgreSQL
- `vnai_ablation_study.ipynb` — Colab notebook template

## Lợi ích

| Metric | CPU local (N=50) | Colab GPU (N=1000) |
|--------|------------------|---------------------|
| Cohort size | 50 | **1000** (20×) |
| Cấu hình | 3 (không LLM) | **5 (đầy đủ)** |
| Thời gian | ~6 giờ | ~2–3 giờ |
| LLM | Không chạy được | **Chạy được** |
