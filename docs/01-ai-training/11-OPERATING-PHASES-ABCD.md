# Vận hành bốn giai đoạn A–B–C–D (train → khóa chỉ số → cleanse → release)

**Phiên bản:** 2.3  
**Cập nhật checklist:** 2026-05-10 — bổ sung ánh xạ **C.4 ↔ `production_pipeline`**  
**Thay thế:** Các playbook dài trước đây (`08`, `09`, `10`, `production-playbook-execution-flow`, phần lớn `00-TRAINING-PIPELINE-OVERVIEW`) được rút gọn thành stub; **tài liệu chạy thực tế là file này.**

**Bối cảnh:** Luồng rule-based / PreLabeler và join lineage queue ↔ `mat.*` đã được siết chặt; cần **một vòng artifact mới** (NER + retrieval + pipeline) thay bản cũ, rồi mới cleanse hàng loạt và release parser/UI.

---

## Checklist trạng thái (đánh dấu trong repo)

**Vị trí hiện tại:** **C.3c đã xong** (migrate có backup). **Bước tiếp:** **C.4a** pilot `production_pipeline` (có `--limit`), rồi **C.4b** full; song song **A** nếu cần model mới trước cleanse lớn.

```
[A] ●·················  mở — artifact train mới chưa khóa
[B] ██████████░░░░░░··  regression OK; KPI NER/E2E chưa ghi vào checklist
[C] ████████████░░░░░░  migrate OK; C.4a/C.4b production_pipeline chưa
[D] ░░░░░░░░░░░░░░░░░░  chưa
```

| ID | Bước | Trạng thái | Ghi chú |
|----|------|------------|---------|
| **A.1** | ETL `ground_truth` → `address_clean_corpus` | [ ] | Chạy khi cần corpus mới |
| **A.2** | Snapshot HF (tuỳ) | [ ] | |
| **A.3** | Train NER → artifact `models/...` | [ ] | `train_ner.py`; cập nhật `config.yaml` sau khi có model |
| **A.4** | Train / eval retrieval | [ ] | `train_siamese_mgte.py` · `evaluate_retriever.py` |
| **A.5** | Embeddings + vector index | [ ] | `compute_embeddings.py` · `setup_vector_indexes.py` |
| **B.1** | Định nghĩa KPI (F1/Acc scope) bằng văn bản | [ ] | Ghi ngưỡng + tập eval cố định |
| **B.2** | Regression PreLabeler | [x] | `run_prelabeler_labeling_cases.py` 136/136; `test_prelabeler_regression.py` OK *(verify 2026-05-10)* |
| **B.3** | `config.yaml` + DB khớp inference | [~] | File tồn tại và trỏ `prq`; **khóa version model** sau A.3 |
| **C.1** | `check_queue_columns.py` | [x] | *(verify 2026-05-10)* |
| **C.2** | `audit_acq_admin_bridge.py` (+ gate G1–G4 tuỳ team) | [x] | Đã dùng trong phiên audit; **re-run** trước migrate production |
| **C.3a** | `migrate_acq_to_admin_v2.py --validate-only` | [x] | *(verify 2026-05-10)* |
| **C.3b** | `migrate_acq_to_admin_v2.py --migrate --dry-run` | [x] | Đã chạy xong *(session trước, ~13 phút)* |
| **C.3c** | `migrate_acq_to_admin_v2.py --migrate --backup` | [x] | **2026-05-10:** backup `prq.address_cleansing_queue_backup_20260510_072119` (437 862 rows); ward_mapping UPDATE 423 025; temp mapping UPDATE prov/dist/ward 313 318 / 11 474 / 2 839 |
| **C.4a** | Pilot cleanse hybrid — **`production_pipeline` + `--limit`** | [ ] | **`python app/ai/production_pipeline.py --config app/ai/config.yaml --limit <N>`** — xem mục **«C.4 — production_pipeline»** bên dưới |
| **C.4b** | Full cleanse — **`production_pipeline` không `--limit`** | [ ] | **`python app/ai/production_pipeline.py --config app/ai/config.yaml`** — sau khi C.4a ổn (chất lượng + lỗi + tải GPU/RAM) |
| **D.1** | `version-info.json` / tag | [ ] | |
| **D.2** | Deploy API | [ ] | |
| **D.3** | Deploy UI | [ ] | |
| **D.4** | Smoke sau deploy | [ ] | |

---

## Chuẩn hóa môi trường (mọi giai đoạn)

```powershell
cd "D:\2.GIT SOURCE\vn-address-intelligence"
$env:PYTHONPATH = "."
$env:PYTHONIOENCODING = "utf-8"   # tuỳ chọn trên Windows
```

DB: `.env` + `app/ai/config.yaml` khớp schema `prq` / `mat`.

---

## Giai đoạn A — Dữ liệu & huấn luyện (để predict tốt hơn)

**Mục tiêu:** Corpus + snapshot nhãn + model NER + retriever + embedding/index đủ để inference chất lượng cao (mục tiêu KPI do team chốt, ví dụ NER eval F1 / token accuracy và retrieval top‑k).

| Bước | Việc | Lệnh / artifact |
|------|------|------------------|
| A.1 | ETL `ground_truth` → `address_clean_corpus` | `python scripts/migration/migrate_ground_truth_to_clean_corpus.py --admin-epoch 2025` (smoke: `--limit 5000`) |
| A.2 | Snapshot HF (tuỳ pipeline) | `python scripts/data/download_hf_ner_address_dataset.py` (tham số xem script) |
| A.3 | Train NER | `python app/ai/train_ner.py` — tham số mẫu trong repo (HF dataset + `--include-ground-truth`, output `models/...`) |
| A.4 | Train / eval retrieval (mGTE hoặc tương đương) | `python app/ai/train_siamese_mgte.py` · `python app/ai/evaluate_retriever.py` |
| A.5 | Embeddings + index vector | `compute_embeddings.py` · `setup_vector_indexes.py` (sau khi DBA bật pgvector nếu cần) |

**Chi tiết kiến trúc từng model:** `01-NER_Entities.md`, `02-PreLabeler.md`, `03-PhoBERT_Siamese.md`, `04-mGTE_Siamese.md`, `05-Qwen_LLM.md`, `06-Performance_Optimization.md`, `07-UI_Parser_Integration.md`.

**Gate A (đề xuất):** Train/eval chạy xong không lỗi; artifact model và log đường dẫn được ghi vào `app/ai/config.yaml` (hoặc biến môi trường deploy).

---

## Giai đoạn B — Khóa chỉ số & kiểm chứng trước cleanse

**Mục tiêu:** Không cleanse hàng loạt cho đến khi đã định nghĩa và đạt KPI trên **tập đánh giá cố định** (tránh nhầm token F1 vs exact match end‑to‑end).

| Bước | Việc | Kiểm chứng |
|------|------|-------------|
| B.1 | Định nghĩa KPI | Ghi rõ: NER (`eval_f1`, …) hay pipeline đầy đủ (`experiment_runner` / benchmark API). |
| B.2 | Regression rule-based | `python scripts/labeling/run_prelabeler_labeling_cases.py` (100% pass) · `python scripts/test/test_prelabeler_regression.py` (`OK`) |
| B.3 | Cấu hình inference | `config.yaml` trỏ đúng model + corpus limit + DB |

**Gate B:** KPI đạt ngưỡng đã chốt + regression PreLabeler pass.

---

## Giai đoạn C — Chuẩn hóa queue (`prq.address_cleansing_queue`)

**Mục tiêu:** Master HC và denorm trên queue đồng bộ với chính sách phiên bản (v2 sau mapping), rồi chạy pipeline hybrid trên batch.

| Bước | Việc | Lệnh |
|------|------|------|
| C.1 | Schema queue vs pipeline | `python scripts/diagnostics/check_queue_columns.py` |
| C.2 | Audit lineage + bridge | `python scripts/diagnostics/audit_acq_admin_bridge.py` |
| C.3 | Migrate admin denorm (dry-run → backup → migrate) | `python scripts/migration/migrate_acq_to_admin_v2.py --validate-only` · `--migrate --dry-run` · `--migrate --backup` |
| C.4 | Cleanse batch | `app/ai/production_pipeline.py` — chi tiết checklist **C.4a / C.4b** |

### C.4 — Lệnh `production_pipeline` (ánh xạ checklist)

Lệnh **`python app/ai/production_pipeline.py --config app/ai/config.yaml --limit <N>`** thuộc **giai đoạn C**, mục checklist **C.4a** (pilot).

| Checklist | Lệnh (mẫu) | Ý nghĩa ngắn |
|-----------|------------|----------------|
| **C.4a** | `python app/ai/production_pipeline.py --config app/ai/config.yaml --limit 500` | Chỉ xử lý tối đa **500** dòng queue thỏa `PENDING` hoặc `address_standardized IS NULL` — kiểm tra chất lượng / lỗi / thời gian trước khi scale. |
| **C.4b** | `python app/ai/production_pipeline.py --config app/ai/config.yaml` | **Không** `--limit`: xử lý **toàn bộ** dòng còn pending/null standardized (có thể rất lâu). |

**Pipeline làm gì (tóm tắt):** đọc `config.yaml` → nạp corpus (mGTE) → NER + retrieval + LLM → ghi `address_standardized`, `processing_status`, confidence, ACS… vào **`prq.address_cleansing_queue`**. **`PYTHONPATH`** phải trỏ root repo nếu chạy từ thư mục gốc (như mục chuẩn hóa môi trường).

**Lineage chuẩn (semantic):** `old_*` ↔ `mat.*.old_id` và **`admin_version`** thống nhất khi giải thích master — xem `.cursor/rules/address-queue-mat-lineage.mdc` và `app/domain/acq_mat_lineage.py`.

**Gate C:** Audit lineage / migrate theo quy trình DBA; **C.4a** pass trước **C.4b**.

---

## Giai đoạn D — Release parser & UI

**Mục tiêu:** Triển khai backend + static UI với **version** và đường dẫn model đã khóa ở B/C.

| Bước | Việc |
|------|------|
| D.1 | Cập nhật `version-info.json` / tag git |
| D.2 | Deploy API (`app/api/server.py`) + env production |
| D.3 | Build/deploy UI (tuỳ hạ tầng; có `scripts/release/publish.ps1`) |
| D.4 | Smoke benchmark / parser sau deploy |

---

## Vòng lặp sau release

Sau cleanse (C), có thể **bơm lại corpus** từ queue đã chuẩn (ETL / nguồn `QUEUE_STANDARDIZED`) rồi lặp A → B với version artifact mới.

---

## Tài liệu legacy (stub)

Các file `08`, `09`, `10`, `production-playbook-execution-flow.md`, `00-TRAINING-PIPELINE-OVERVIEW.md`, `ai-training-workflow-summary.md`, `training-phase-plan.md`, v.v. chỉ còn **redirect** tới file này để giữ link cũ và giảm trùng lặp.
