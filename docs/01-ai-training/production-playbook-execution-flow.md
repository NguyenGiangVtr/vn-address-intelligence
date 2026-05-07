# Production Playbook Execution Flow (Runbook + KPI)

Tài liệu này mô tả chi tiết thứ tự chạy production theo playbook:

1. ETL  
2. HF snapshot  
3. Train NER  
4. Train/Eval retrieval  
5. Embeddings/Index  
6. Production pipeline

Mục tiêu là để bạn tự chạy, tự kiểm nghiệm và ghi nhận KPI theo từng bước.

## 0) Prerequisites

- Đứng tại root repo: `D:\2.GIT SOURCE\vn-address-intelligence`
- Dùng PowerShell
- DB/Postgres, pgvector và các biến môi trường đã sẵn sàng (`.env`)
- Python env có đủ dependency (`datasets`, `transformers`, `sentence-transformers`, `seqeval`, `psycopg2`, ...)

Thiết lập import path cho toàn bộ lệnh:

```powershell
$env:PYTHONPATH='.'
```

---

## 1) ETL: `ground_truth -> address_clean_corpus`

### Command (production full)

```powershell
python scripts/migration/migrate_ground_truth_to_clean_corpus.py --admin-epoch 2025
```

### Command (smoke-run trước khi full)

```powershell
python scripts/migration/migrate_ground_truth_to_clean_corpus.py --admin-epoch 2025 --limit 5000
```

### KPI cần ghi nhận

- `loaded_rows`: tổng số dòng đọc từ `prq.ground_truth`
- `inserted`, `updated`, `skipped` (từ log cuối)
- `idempotent_check`: chạy lại 1 lần cùng tham số, kỳ vọng `inserted` giảm mạnh (hoặc gần 0) và chủ yếu `updated/skip`
- `error_rate`: số lỗi / tổng record ETL (mục tiêu gần 0)

### Tiêu chí pass

- ETL chạy xong không crash DB connection
- Có log kết thúc với `inserted/updated/skipped`
- Chạy lại idempotent không tạo tăng đột biến bản ghi mới

### Mẫu ghi kết quả

- ETL duration: `...`
- loaded_rows: `...`
- inserted: `...`
- updated: `...`
- skipped: `...`
- idempotent rerun result: `...`
- pass/fail: `...`

---

## 2) HF Snapshot: `ner-address-standard-dataset`

### Command

```powershell
python scripts/data/download_hf_ner_address_dataset.py `
  --dataset dathuynh1108/ner-address-standard-dataset `
  --output-dir data/hf_snapshots `
  --train-limit 50000 `
  --test-limit 5000 `
  --streaming
```

> Ghi chú: script đã có fallback tự động sang streaming nếu mode thường lỗi `DatasetGenerationError`.

### KPI cần ghi nhận

- `snapshot_dir`: thư mục snapshot tạo mới
- `train_count`, `test_count` (in ra JSON cuối lệnh)
- `metadata_integrity`: có đủ `train.jsonl`, `test.jsonl`, `metadata.json`
- `reproducibility_key`: timestamp + dataset id trong metadata

### Tiêu chí pass

- Command chạy thành công, in JSON metadata
- Có đủ 3 file snapshot

### Mẫu ghi kết quả

- snapshot_dir: `...`
- train_count: `...`
- test_count: `...`
- files_ok: `true/false`
- pass/fail: `...`

---

## 3) Train NER (PhoBERT)

### Command (khuyến nghị production)

```powershell
python app/ai/train_ner.py `
  --hf-dataset dathuynh1108/ner-address-standard-dataset `
  --hf-max-train 50000 `
  --hf-max-eval 5000 `
  --include-ground-truth `
  --gt-max-train 10000 `
  --output models/phobert-ner-vn-playbook `
  --epochs 15 `
  --batch-size 16 `
  --lr 2e-5
```

### KPI cần ghi nhận

- `eval_f1`, `eval_precision`, `eval_recall`, `eval_loss`
- `token_accuracy` (nội bộ script tính)
- `n_train`, `n_eval`
- `training_time`
- `model_artifact`: có model trong thư mục output + `training_log.json`

### Tiêu chí pass

- `eval_f1 >= 0.85` (theo playbook)
- Không lỗi schema label (10 nhãn bắt buộc)
- Lưu được artifact model

### Mẫu ghi kết quả

- n_train / n_eval: `... / ...`
- eval_f1: `...`
- eval_precision: `...`
- eval_recall: `...`
- eval_loss: `...`
- artifact_ok: `true/false`
- pass/fail: `...`

---

## 4) Retrieval: Train + Eval

## 4.1 Train Siamese mGTE

### Command

```powershell
python app/ai/train_siamese_mgte.py `
  --output models/mgte-siamese-vn-playbook `
  --model-name Alibaba-NLP/gte-multilingual-base `
  --limit 20000 `
  --epochs 1 `
  --batch-size 32 `
  --lr 2e-5
```

### KPI cần ghi nhận

- `pair_count_train` (số cặp old/new dùng train)
- `train_duration`
- `artifact_ok` (thư mục model được lưu)

## 4.2 Evaluate Retriever

### Command

```powershell
python app/ai/evaluate_retriever.py `
  --model-name models/mgte-siamese-vn-playbook `
  --top-k 10 `
  --limit 2000
```

### KPI cần ghi nhận

- `top1`
- `top5`
- `mrr@10`
- `ndcg@10`
- `samples`

### Tiêu chí pass (đề xuất vận hành)

- `top1 >= 0.70`
- `top5 >= 0.90`
- `mrr@10 >= 0.80`
- `ndcg@10 >= 0.85`

### Mẫu ghi kết quả

- pair_count_train: `...`
- top1: `...`
- top5: `...`
- mrr@10: `...`
- ndcg@10: `...`
- pass/fail: `...`

---

## 5) Embeddings + Vector Index

## 5.1 Compute embeddings

### Command

```powershell
python compute_embeddings.py
```

### KPI cần ghi nhận

- `total_addresses`
- `%has_mgte`
- `%has_phobert`
- `%has_both`
- `checkpoint_progress` trong `reports/*_embedding_checkpoint.json`

### Tiêu chí pass

- Hoàn tất vòng lặp embedding, tỷ lệ phủ embeddings cao (ưu tiên gần 100%)

## 5.2 Setup/benchmark vector indexes

### Command

```powershell
python setup_vector_indexes.py
```

### KPI cần ghi nhận

- pgvector extension/version
- index tạo thành công (HNSW hoặc fallback IVFFlat)
- `p95 query latency` (log benchmark cuối script)

### Tiêu chí pass

- Có index vector hoạt động
- `p95 < 10ms` (SLA playbook)

### Mẫu ghi kết quả

- has_mgte / has_phobert / has_both: `...`
- index_type: `HNSW/IVFFlat`
- p95_latency_ms: `...`
- pass/fail: `...`

## 5.3 pgvector chưa cài trên Postgres (DBA unblock)

Nếu `python setup_vector_indexes.py` kết thúc với lỗi kiểu:

`could not open extension control file ".../postgresql/.../extension/vector.control": No such file or directory`

thì **extension pgvector chưa được cài trên server** (không phải lỗi Python). Cần DBA/OS package:

- Cài `pgvector` đúng major version PostgreSQL (ví dụ PG 12), hoặc dùng image/container đã có sẵn pgvector.
- Sau đó (superuser): `CREATE EXTENSION IF NOT EXISTS vector;`
- Khi đó mới chạy lại `setup_vector_indexes.py` để tạo HNSW/IVFFlat và benchmark p95.

**Lưu ý schema corpus hiện tại:** nếu cột `mgte_embedding` / `phobert_embedding` đang là `jsonb`, script `compute_embeddings.py` vẫn ghi được embedding dạng JSON; để index vector thực sự hoạt động cần migration sang kiểu `vector(768)` (hoặc kích thước đúng model) **sau** khi pgvector đã bật.

---

## 5.4 KPI đã ghi nhận (môi trường playbook — tham chiếu)

| Bước | KPI | Giá trị tham chiếu | Ghi chú |
|------|-----|-------------------|---------|
| NER | `eval_f1` | **0.951** | `models/phobert-ner-vn-playbook/training_log.json` (train nhỏ 6k/800 eval, 2 epoch — scale lên 50k×15 epoch trên GPU khi production) |
| Retrieval | top1 / top5 / mrr@10 / ndcg@10 | **0.954 / 0.968 / 0.960 / 0.963** | `evaluate_retriever.py --limit 500` |
| Embeddings | incremental | `compute_embeddings.py --max-batches 2` | Smoke; full run bỏ `--max-batches` |
| Vector index | pgvector | **blocked** | Xem §5.3 |

---

## 6) Production Pipeline

### Command (smoke-run)

```powershell
python app/ai/production_pipeline.py --config app/ai/config.yaml --limit 500
```

### Command (production batch/full)

```powershell
python app/ai/production_pipeline.py --config app/ai/config.yaml
```

### KPI cần ghi nhận

- `records_processed`
- `throughput_records_per_min`
- `p95_end_to_end_latency_ms` (nếu có APM/log collector)
- `error_rate`
- `acs_decision_distribution`: auto-accept/convert/suggest/reject

### Tiêu chí pass

- throughput `>= 100 record/phút` (SLA playbook)
- error rate thấp và ổn định
- pipeline không fail ở load model/corpus

### Mẫu ghi kết quả

- processed: `...`
- throughput_rpm: `...`
- p95_latency_ms: `...`
- error_rate: `...`
- acs_decision_distribution: `...`
- pass/fail: `...`

---

## 7) Bảng tổng hợp KPI cuối cùng

Sau khi chạy xong toàn bộ, điền bảng sau:

| Step | KPI chính | Kết quả thực tế | Target | Pass/Fail |
|---|---|---|---|---|
| ETL | inserted/updated/skipped + idempotent | ... | Idempotent + no crash | ... |
| HF snapshot | train/test count + metadata files | ... | đủ file snapshot | ... |
| NER | eval_f1 | ... | >= 0.85 | ... |
| Retrieval Eval | top1/top5/mrr@10/ndcg@10 | ... | theo ngưỡng đã chốt | ... |
| Embedding | coverage mgte/phobert | ... | gần 100% | ... |
| Vector Index | p95 latency | ... | < 10ms | ... |
| Production Pipeline | throughput + error_rate | ... | >=100 rpm + stable | ... |

---

## 8) Gợi ý trình tự chạy thực tế (không gián đoạn)

```powershell
$env:PYTHONPATH='.'

# 1) ETL
python scripts/migration/migrate_ground_truth_to_clean_corpus.py --admin-epoch 2025

# 2) HF snapshot
python scripts/data/download_hf_ner_address_dataset.py --dataset dathuynh1108/ner-address-standard-dataset --output-dir data/hf_snapshots --train-limit 50000 --test-limit 5000

# 3) NER
python app/ai/train_ner.py --hf-dataset dathuynh1108/ner-address-standard-dataset --hf-max-train 50000 --hf-max-eval 5000 --include-ground-truth --gt-max-train 10000 --output models/phobert-ner-vn-playbook --epochs 15 --batch-size 16 --lr 2e-5

# 4) Retrieval train/eval
python app/ai/train_siamese_mgte.py --output models/mgte-siamese-vn-playbook --model-name Alibaba-NLP/gte-multilingual-base --limit 20000 --epochs 1 --batch-size 32 --lr 2e-5
python app/ai/evaluate_retriever.py --model-name models/mgte-siamese-vn-playbook --top-k 10 --limit 2000

# 5) Embeddings + Index
python compute_embeddings.py
python setup_vector_indexes.py

# 6) Production pipeline
python app/ai/production_pipeline.py --config app/ai/config.yaml

# 6b) Pilot 1k + audit + summary (Phase 4.2–4.4)
# PYTHONUNBUFFERED=1 helps Progress: lines appear every 50 rows without pipe buffering.
$env:PYTHONUNBUFFERED='1'; python app/ai/production_pipeline.py --config app/ai/config.yaml --limit 1000
python scripts/diagnostics/audit_pilot_vs_gt.py --window-minutes 120 --limit 1000
python scripts/diagnostics/full_cleanse_summary.py

# 6c) Full cleanse 500k (Phase 4.3) — hoặc chạy script PowerShell
powershell -File scripts/run_full_cleanse_500k.ps1
```

Nếu muốn, sau khi bạn chạy xong, mình sẽ tổng hợp log thực tế của bạn thành một `KPI report` chuẩn release (go/no-go) ngay trong repo.
