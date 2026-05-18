# `scripts/flow` — luồng end-to-end VNAI + đồng bộ báo cáo LaTeX

## Mục tiêu

Một lần chạy lần lượt:

1. `py_compile` các module then chốt  
2. Regression PreLabeler (`run_prelabeler_labeling_cases.py`, `test_prelabeler_regression.py`)  
3. *(tuỳ DB)* `audit_acq_admin_bridge.py --write-json reports/audit_acq_admin_bridge_last.json`  
4. *(tuỳ DB)* `python -m app.ai.experiment_runner --config app/ai/config.yaml --no-llm`  
5. *(tuỳ DB)* `production_pipeline.py --limit <N>` (pilot)  
6. *(tuỳ HF + torch)* `train_ner.py` smoke trên dataset HF chuẩn (ít epoch / ít mẫu — **không** thay thế huấn luyện production đầy đủ)  
7. `generate_scientific_report_metrics.py` → cập nhật `docs/scientific-report/vnai-generated-metrics.tex` (LaTeX metrics)

## Windows (PowerShell)

```powershell
cd "D:\2.GIT SOURCE\vn-address-intelligence"
.\scripts\flow\run_full_vnai_flow.ps1
# PostgreSQL không mở / Connection refused: vẫn chạy train + metrics (bỏ qua experiment + pipeline):
.\scripts\flow\run_full_vnai_flow.ps1 -OptionalDb
# Hoàn toàn không gọi DB:
.\scripts\flow\run_full_vnai_flow.ps1 -SkipDb
# Không train NER:
.\scripts\flow\run_full_vnai_flow.ps1 -SkipTrain
```

## Linux / macOS / Git Bash

```bash
cd /path/to/vn-address-intelligence
chmod +x scripts/flow/run_full_vnai_flow.sh   # một lần
./scripts/flow/run_full_vnai_flow.sh
# SKIP_DB=1 ./scripts/flow/run_full_vnai_flow.sh
# OPTIONAL_DB=1 ./scripts/flow/run_full_vnai_flow.sh   # audit fail → skip rest of DB
# SKIP_TRAIN=1 PIPELINE_LIMIT=50 ./scripts/flow/run_full_vnai_flow.sh
```

## Biên dịch báo cáo

```powershell
cd docs\scientific-report
xelatex vnai-chapters-master.tex
xelatex vnai-chapters-master.tex
```

## Ghi chú

- Bước DB cần `.env` / `app/ai/config.yaml` trùng môi trường PostgreSQL (máy chủ phải chấp nhận kết nối). Nếu lỗi **Connection refused**, dùng **`-OptionalDb`** (PowerShell) hoặc **`OPTIONAL_DB=1`** (bash), hoặc **`-SkipDb`**.  
- Bước train cần mạng (tải HF) và RAM/GPU đủ cho PhoBERT 1 epoch smoke.  
- `vnai-generated-metrics.tex` **ghi đè** mỗi lần chạy generator; nên commit sau khi đã xác minh số trên snapshot production.
