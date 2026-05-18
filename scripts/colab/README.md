# Google Colab Integration Scripts

Scripts để chạy thực nghiệm SUPA-Bench trên Google Colab với GPU.

## Workflow

### Phase 1: Chuẩn bị dữ liệu (local)

```bash
# Export tất cả files vào folder colab_vnai/ (1 lệnh duy nhất)
python scripts/colab/export_all_for_colab.py

# Upload lên Google Drive:
#    - Vào https://drive.google.com
#    - Upload toàn bộ folder "colab_vnai" vào "My Drive"
#    - Kết quả: /MyDrive/colab_vnai/ chứa 4 files (~3.94 MB)
```

### Phase 2: Chạy trên Colab

Mở `vnai_ablation_study.ipynb` trên Google Colab và chạy từng cell.

**Thời gian ước tính (GPU T4):**
- A1 (NER + TF-IDF + LLM): ~30 phút
- A2 (NER + TF-IDF): ~20 phút
- A3 (TF-IDF only): ~20 phút
- A4 (NER + LLM): ~25 phút
- **Tổng: ~2–3 giờ**

**Lưu ý:**
- Notebook sử dụng **TF-IDF retriever** thay vì mGTE do vấn đề tương thích CUDA
- TF-IDF nhanh hơn và ổn định hơn trên Colab
- Kết quả vẫn có giá trị cho ablation study

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

- `export_all_for_colab.py` — **Export tất cả (1 lệnh)** → folder colab_vnai/
- `export_ground_truth_sqlite.py` — Export PostgreSQL → SQLite
- `export_noise_profiles.py` — Export noise profiles → JSON
- `export_src_for_colab.py` — Export source code → ZIP
- `import_colab_results.py` — Import CSV từ Colab → PostgreSQL
- `vnai_ablation_study.ipynb` — Colab notebook template

## Lợi ích

| Metric | CPU local (N=50) | Colab GPU (N=1000) |
|--------|------------------|---------------------|
| Cohort size | 50 | **1000** (20×) |
| Cấu hình | 3 (không LLM) | **5 (đầy đủ)** |
| Thời gian | ~6 giờ | ~2–3 giờ |
| LLM | Không chạy được | **Chạy được** |

## Troubleshooting

### "No such file or directory" khi setup
**Nguyên nhân:** Chưa upload files lên Google Drive hoặc sai đường dẫn.

**Giải pháp:**
1. Kiểm tra đã upload đủ 4 files vào Drive:
   - `ground_truth.db`
   - `noise_profiles.json`
   - `vnai_src.zip`
   - `vnai_ablation_study.ipynb`
2. Đảm bảo đường dẫn là `/content/drive/MyDrive/colab_vnai/`
3. Nếu thư mục Drive có tên khác, sửa đường dẫn trong notebook cell đầu tiên

### "ModuleNotFoundError: No module named 'app'"
**Nguyên nhân:** Source code chưa được extract hoặc không có trong Python path.

**Giải pháp:**
1. Kiểm tra đã upload `vnai_src.zip` vào Drive
2. Chạy lại Cell 1 để extract source code
3. Kiểm tra `/content/src/app/` có tồn tại không

### "AcceleratorError: CUDA error: device-side assert triggered"
**Nguyên nhân:** mGTE model không tương thích với dữ liệu tiếng Việt trên GPU.

**Giải pháp:** Đã fix - notebook hiện sử dụng TF-IDF retriever thay vì mGTE. TF-IDF ổn định hơn và không gặp lỗi CUDA.

### Colab disconnect sau vài giờ
**Giải pháp:** 
- Chạy từng config riêng lẻ (A1, A2, A3, A4)
- Download CSV sau mỗi config
- Import từng phần về PostgreSQL

### Out of memory
**Giải pháp:** 
- TF-IDF corpus đã giảm xuống 10,000 địa chỉ
- Nếu vẫn OOM, giảm xuống 5,000 trong Cell 2
