# `scripts/experiments` — thí nghiệm có kiểm soát

## SUPA-Bench (`supa_benchmark.py`)

**Quy tắc:** không `INSERT`/`UPDATE`/`DELETE` trên `prq.ground_truth` — chỉ `SELECT` trích mẫu.

**Chạy một lần (demo / lặp lại):**

```powershell
python scripts/experiments/supa_benchmark.py workflow --n 1000 --seed 42
```

Sau khi điền `pred_standardized` trong CSV:

```powershell
python scripts/experiments/supa_benchmark.py workflow --skip-extract --run-id <id> --preds path/to/preds.csv --source-note "..."
```

Hoặc: `.\scripts\experiments\run_supa_benchmark.ps1` · `bash scripts/experiments/run_supa_benchmark.sh`  
**Runbook đầy đủ:** `docs/scientific-report/SUPA-BENCH-RUNBOOK.md` (từ thư mục gốc repo).

1. Áp DDL (một lần trên DB — **không cần `psql`** nếu dùng Python):

   `python scripts/sql/apply_sql_file.py scripts/migration/20260209_prq_supa_benchmark_tables.sql`

2. Trích + nhiễu + ghi `prq.supa_benchmark_run` / `prq.supa_benchmark_specimen`:

   `python scripts/experiments/supa_benchmark.py extract --n 10000 --seed 42`

3. Xuất CSV để chạy chuẩn hóa **bên ngoài** (pipeline bạn mô tả trong luận; cùng snapshot model):

   `python scripts/experiments/supa_benchmark.py export-specimens --out reports/supa_specimens_run1.csv`

4. Sau khi có cột dự đoán (vd. điền `pred_standardized` trên CSV hoặc file tương đương), nhập lại DB **kèm ghi chú nguồn gốc** (bắt buộc cho báo cáo):

   `python scripts/experiments/supa_benchmark.py import-preds --csv path/to/preds.csv --source-note "production_pipeline; config=app/ai/config.yaml; commit=..."`

   → sinh `reports/supa_benchmark_last_import_manifest.json`.

5. Đo + ghi JSON:

   `python scripts/experiments/supa_benchmark.py eval`

6. Đồng bộ LaTeX:

   `python scripts/experiments/supa_benchmark.py export-tex`

**Vì sao không có lệnh `normalize` tích hợp `production_pipeline`:** pipeline nhắm `address_cleansing_queue`; chuỗi export→import giữ provenance rõ. Chi tiết: `Protocol-Synthetic-User-Perturbation-Benchmark-Google-Ground-Truth.md` mục 2.2.

Đặc tả đầy đủ: `docs/scientific-report/Protocol-Synthetic-User-Perturbation-Benchmark-Google-Ground-Truth.md`.
