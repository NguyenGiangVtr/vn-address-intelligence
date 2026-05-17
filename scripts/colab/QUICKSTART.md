# Colab Integration - Quick Start Guide

## Bước 1: Chuẩn bị dữ liệu (local, ~5 phút)

```bash
# Export ground_truth
python scripts/colab/export_ground_truth_sqlite.py --limit 15000 --output ground_truth.db

# Export noise profiles
python scripts/colab/export_noise_profiles.py --output noise_profiles.json
```

**Upload lên Google Drive:**
- Tạo thư mục `colab_vnai/` trong Drive
- Upload `ground_truth.db` (~5–10 MB)
- Upload `noise_profiles.json` (~50 KB)
- Upload `vnai_ablation_study.ipynb`

---

## Bước 2: Chạy trên Colab (~2–3 giờ)

1. Mở `vnai_ablation_study.ipynb` trên Google Colab
2. Runtime → Change runtime type → **GPU (T4)**
3. Chạy từng cell theo thứ tự
4. Download `ablation_n1000_results.csv` ở cell cuối

**Lưu ý:**
- Cell 1 (Setup): ~5 phút
- Cell 2 (Load models): ~10 phút
- Cell 3 (Extract cohort): ~1 phút
- Cell 4–7 (Run A1–A4): ~20–30 phút/config
- Cell 8 (Export): ~1 phút

---

## Bước 3: Import kết quả (local, ~15 phút)

```bash
# Import CSV
python scripts/colab/import_colab_results.py --csv ablation_n1000_results.csv

# Chạy eval (xem output của import để lấy run_id)
python scripts/experiments/supa_benchmark.py eval --run-id 101
python scripts/experiments/supa_benchmark.py eval --run-id 102
python scripts/experiments/supa_benchmark.py eval --run-id 103
python scripts/experiments/supa_benchmark.py eval --run-id 104

# Aggregate
python scripts/experiments/supa_benchmark.py aggregate-runs \
    --run-ids 101,102,103,104 \
    --out-json reports/ablation_n1000_colab_aggregate.json
```

---

## Bước 4: Cập nhật báo cáo

Sau khi có `ablation_n1000_colab_aggregate.json`, cập nhật:

- **Mục 9.10.1:** Bảng kết quả Ablation N=1000
- **Mục 10.0:** Kết luận có LLM
- **Mục 10.4:** Bỏ hạn chế "không đánh giá LLM"

---

## Troubleshooting

### Colab timeout sau 12 giờ
→ Chạy từng config riêng lẻ, download CSV sau mỗi config

### Out of memory
→ Giảm `corpus_limit` xuống 8000 hoặc 10000

### Model download chậm
→ Cache models trong Drive, copy vào `/content/` thay vì download

---

## So sánh CPU vs Colab

| Metric | CPU local (N=50) | Colab GPU (N=1000) |
|--------|------------------|---------------------|
| Cohort size | 50 | **1000** (20×) |
| Cấu hình | 3 (không LLM) | **4–5 (có LLM)** |
| Thời gian | ~6 giờ | ~2–3 giờ |
| LLM | Không chạy được | **Chạy được** |
| Chi phí | $0 | $0 (free tier) |
