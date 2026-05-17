# Colab Integration - Quick Start Guide

## Bước 1: Chuẩn bị dữ liệu (local, ~5 phút)

```bash
# Export tất cả files vào folder colab_vnai/ (1 lệnh duy nhất)
python scripts/colab/export_all_for_colab.py
```

**Hoặc export từng file riêng lẻ:**
```bash
python scripts/colab/export_ground_truth_sqlite.py
python scripts/colab/export_noise_profiles.py
python scripts/colab/export_src_for_colab.py
copy scripts\colab\vnai_ablation_study.ipynb colab_vnai\
```

**Upload lên Google Drive:**
1. Vào [Google Drive](https://drive.google.com)
2. Upload toàn bộ folder `colab_vnai/` vào "My Drive"
3. Kết quả: `/MyDrive/colab_vnai/` chứa 4 files (~3.94 MB):
   - `ground_truth.db` (3.67 MB, 15000 rows)
   - `noise_profiles.json` (1.3 KB)
   - `vnai_src.zip` (260 KB, source code)
   - `vnai_ablation_study.ipynb` (16 KB)

---

## Bước 2: Chạy trên Colab (~2–3 giờ)

1. Mở `vnai_ablation_study.ipynb` trên Google Colab
2. Runtime → Change runtime type → **GPU (T4)**
3. Chạy từng cell theo thứ tự
4. Download `ablation_n1000_results.csv` ở cell cuối

**Lưu ý:**
- Cell 1 (Setup): ~5 phút
- Cell 2 (Load models): ~10 phút
  - **Sử dụng TF-IDF retriever thay vì mGTE** (do mGTE có lỗi CUDA với dữ liệu tiếng Việt)
  - TF-IDF encoding: ~2-3 phút cho 10,000 địa chỉ
- Cell 3 (Extract cohort): ~1 phút
- Cell 4–8 (Run A1–A5): ~20–30 phút/config
  - **5 configs × 5,000 mẫu = 25,000 specimens tổng cộng**
- Cell 9 (Export): ~1 phút

---

## Bước 3: Import kết quả (local, ~15 phút)

```powershell
# Import CSV (PowerShell - single line)
python scripts/colab/import_colab_results.py --csv scripts/colab/ablation_n1000_results.csv

# Chạy eval cho từng run (xem output của import để lấy run_id)
python scripts/experiments/supa_benchmark.py eval --run-id 100
python scripts/experiments/supa_benchmark.py eval --run-id 101
python scripts/experiments/supa_benchmark.py eval --run-id 102
python scripts/experiments/supa_benchmark.py eval --run-id 103
python scripts/experiments/supa_benchmark.py eval --run-id 104

# Aggregate (PowerShell - single line, dùng min/max thay vì run-ids)
python scripts/experiments/supa_benchmark.py aggregate-runs --min-run-id 100 --max-run-id 104 --out-json reports/ablation_n1000_colab_aggregate.json
```

---

## Bước 4: Cập nhật báo cáo

Sau khi có `ablation_n1000_colab_aggregate.json`, cập nhật:

- **Mục 9.10.1:** Bảng kết quả Ablation N=5000 (5 configs × 5,000 mẫu)
  - A1_FULL: EM@v2 = 66.58%, F1 Đường = 82.71%
  - A2_NER_TFIDF: EM@v2 = 60.98%
  - A2_NER_MGTE: EM@v2 = 60.98%
  - A3_MGTE_ONLY: EM@v2 = 60.98%
  - A4_NER_LLM: EM@v2 = 8.46% (thất bại)
- **Mục 10.0:** Kết luận có đánh giá LLM trên GPU
- **Mục 10.4:** Cập nhật hạn chế - đã đánh giá LLM nhưng kết quả kém

---

## Troubleshooting

### Files not found: "No such file or directory"
→ Kiểm tra đã upload đủ 4 file vào `/content/drive/MyDrive/colab_vnai/`:
  - `ground_truth.db`
  - `noise_profiles.json`
  - `vnai_src.zip`
  - `vnai_ablation_study.ipynb`

### ModuleNotFoundError: No module named 'app'
→ Kiểm tra đã upload `vnai_src.zip` và Cell 1 đã extract thành công.
→ Chạy lại Cell 1 để extract source code.

### AcceleratorError: CUDA error (mGTE)
→ Đã fix: Notebook sử dụng TF-IDF retriever thay vì mGTE.
→ TF-IDF ổn định hơn và không gặp lỗi CUDA với dữ liệu tiếng Việt.

### Colab timeout sau 12 giờ
→ Chạy từng config riêng lẻ, download CSV sau mỗi config

### Out of memory
→ Giảm corpus size từ 10,000 xuống 5,000 trong Cell 2

### Model download chậm
→ Cache models trong Drive, copy vào `/content/` thay vì download

---

## So sánh CPU vs Colab

| Metric | CPU local (N=50) | Colab GPU (N=5000/config) |
|--------|------------------|---------------------------|
| Cohort size | 50 | **5000 × 5 configs = 25,000** |
| Cấu hình | 3 (không LLM) | **5 (có LLM)** |
| Thời gian | ~6 giờ | ~2–3 giờ |
| LLM | Không chạy được | **Chạy được** |
| Chi phí | $0 | $0 (free tier) |
| Kết quả tốt nhất | A2 (retrieval): 4% EM | **A1_FULL: 66.58% EM** |
| Kết quả LLM | N/A | **A4: 8.46% EM (thất bại)** |
