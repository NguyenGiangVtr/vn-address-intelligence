# Vận hành bốn giai đoạn A–B–C–D (train → khóa chỉ số → cleanse → release)

**Phiên bản:** 2.7  
**Cập nhật checklist:** 2026-05-10 — đồng bộ **snapshot audit bridge** (số liệu thực đo) + báo cáo khoa học `docs/scientific-report`  
**Thay thế:** Các playbook dài trước đây (`08`, `09`, `10`, `production-playbook-execution-flow`, phần lớn `00-TRAINING-PIPELINE-OVERVIEW`) được rút gọn thành stub; **tài liệu chạy thực tế là file này.**

**Bối cảnh:** Luồng rule-based / PreLabeler và join lineage queue ↔ `mat.*` đã được siết chặt; cần **một vòng artifact mới** (NER + retrieval + pipeline) thay bản cũ, rồi mới cleanse hàng loạt và release parser/UI.

---

## Checklist trạng thái (đánh dấu trong repo)

**Vị trí hiện tại:** **B.1 đã khóa giao thức** (P‑F1 + P‑Acc) · **C.3d chấp nhận** · **C.3c xong**. **Bước tiếp:** **A** (đạt **P‑F1** & **P‑Acc**) → **C.4a/C.4b** cleanse; **B.3** khóa artifact sau train.

```
[A] ●·················  mở — cần train/eval: P‑F1 & P‑Acc > 96% (**B.1.1**)
[B] ████████████████░░  B.1+B.2 OK; B.3 chờ artifact khóa trong config
[C] ██████████████░░░░  C.3 + C.3d OK; C.4a/C.4b pipeline chưa
[D] ░░░░░░░░░░░░░░░░░░  chưa
```

| ID | Bước | Trạng thái | Ghi chú |
|----|------|------------|---------|
| **A.1** | ETL `ground_truth` → `address_clean_corpus` | [ ] | Chạy khi cần corpus mới |
| **A.2** | Snapshot HF (tuỳ) | [ ] | |
| **A.3** | Train NER → artifact `models/...` | [ ] | `train_ner.py`; cập nhật `config.yaml` sau khi có model |
| **A.4** | Train / eval retrieval | [ ] | `train_siamese_mgte.py` · `evaluate_retriever.py` |
| **A.5** | Embeddings + vector index | [ ] | `compute_embeddings.py` · `setup_vector_indexes.py` |
| **B.1** | Định nghĩa KPI (F1/Acc scope) bằng văn bản | [x] | **Chốt giao thức:** chỉ báo đạt ngưỡng khi đủ **bộ chỉ số primary** (**mục B.1**). Chỉ số **bổ trợ** báo trong luận/bảng nhưng **không thay gate B**. |
| **B.2** | Regression PreLabeler | [x] | `run_prelabeler_labeling_cases.py` 136/136; `test_prelabeler_regression.py` OK *(verify 2026-05-10)* |
| **B.3** | `config.yaml` + DB khớp inference | [~] | File tồn tại và trỏ `prq`; **khóa version model** sau A.3 |
| **C.1** | `check_queue_columns.py` | [x] | *(verify 2026-05-10)* |
| **C.2** | `audit_acq_admin_bridge.py` (+ gate G1–G4 tuỳ team) | [x] | Đã dùng trong phiên audit; **re-run** trước migrate production |
| **C.3a** | `migrate_acq_to_admin_v2.py --validate-only` | [x] | *(verify 2026-05-10)* |
| **C.3b** | `migrate_acq_to_admin_v2.py --migrate --dry-run` | [x] | Đã chạy xong *(session trước, ~13 phút)* |
| **C.3c** | `migrate_acq_to_admin_v2.py --migrate --backup` | [x] | **2026-05-10:** backup `prq.address_cleansing_queue_backup_20260510_072119` (437 862 rows); ward_mapping UPDATE 423 025; temp mapping UPDATE prov/dist/ward 313 318 / 11 474 / 2 839 |
| **C.3d** | Post-migrate: audit + `--validate-only` | [x] | **Owner chấp nhận** *(2026-05-10).* **Snapshot audit thực đo** (lệnh `python scripts/diagnostics/audit_acq_admin_bridge.py`, kết thúc chạy ~2026-05-10 15:28 +07): queue **437 862** rows; **G1 pass**; **G2 fail** — coverage triple lineage inner **96,61%** (ngưỡng script ≥99,9%); **G3/G4 fail** — denorm P/D/W cùng `admin_version` + đúng phân cấp (và current): **431 509** aligned (**98,55%**), **6 353** rows fail theo định nghĩa SQL gate. Chi tiết bảng mô tả học xem `docs/scientific-report` (Ch.~5). Tiếp tục vận hành / cleanse không bị chặn bởi gate tự động sau khi owner chấp nhận. |
| **C.4a** | Pilot cleanse hybrid — **`production_pipeline` + `--limit`** | [ ] | **`python app/ai/production_pipeline.py --config app/ai/config.yaml --limit <N>`** — xem mục **«C.4 — production_pipeline»** bên dưới |
| **C.4b** | Full cleanse — **`production_pipeline` không `--limit`** | [ ] | **`python app/ai/production_pipeline.py --config app/ai/config.yaml`** — sau khi C.4a ổn (chất lượng + lỗi + tải GPU/RAM) |
| **D.1** | `version-info.json` / tag | [ ] | |
| **D.2** | Deploy API | [ ] | |
| **D.3** | Deploy UI | [ ] | |
| **D.4** | Smoke sau deploy | [ ] | |

### Hoàn thiện lộ trình — thứ tự đề xuất (đến khi đánh [x] hết phần bạn cần)

1. ~~**C.3d**~~ — **[x]** Đã audit + validate-only; owner chấp nhận.
2. ~~**B.1**~~ — **[x]** Giao thức: **P‑F1**, **P‑Acc** (>96%, cùng tập — **B.1.1**); chỉ số **S‑*** chỉ báo cáo (**B.1.2**).
3. **A*** — A.1→A.5; chứng minh **B.1.1** + bảng **B.1.2** trong báo cáo thực nghiệm; cập nhật **`models.*.local_path`** / `NER_MODEL_ID` → **[x]** **B.3**.
4. **C.4a** — Pilot: `production_pipeline` với `--limit` nhỏ (vd. 50→500), xem lỗi `ERROR`, chất lượng `address_standardized`, thời gian/GPU → đánh **[x]** khi tiêu chí pilot pass.
5. **C.4b** — Full cleanse: bỏ `--limit` (thường chạy off-peak); sau đó **re-run C.3d** hoặc audit mẫu để xác nhận.
6. **Vòng corpus** *(tuỳ)* — ETL / nguồn `QUEUE_STANDARDIZED` vào `address_clean_corpus` rồi embeddings/index (mục «Vòng lặp sau release»).
7. **D.1–D.4** — Bump `version-info.json`, deploy API/UI, smoke benchmark/parser.

**Tiêu chí “xong giai đoạn C” (gợi ý):** C.3c + C.4b đã chạy; tỷ lệ `processing_status = ERROR` trong pilot/full nằm trong ngưỡng team; mẫu QA địa chỉ chấp nhận được.

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
| B.1 | Định nghĩa KPI | Đã chốt — **mục B.1 — KPI nghiên cứu** bên dưới. |
| B.2 | Regression rule-based | `python scripts/labeling/run_prelabeler_labeling_cases.py` (100% pass) · `python scripts/test/test_prelabeler_regression.py` (`OK`) |
| B.3 | Cấu hình inference | `config.yaml` trỏ đúng model + corpus limit + DB |

### B.1 — KPI nghiên cứu (**giao thức đo đã khóa**, 2026-05-10)

**Nguyên tắc:** phân biệt **Primary** (dùng để **Gate B**: khóa chất lượng nghiên cứu reproducible) và **Bổ trợ** (bảng/phụ lục, không thay Gate B).

#### B.1.1 Primary — đồng thời đạt cả hai, cùng một tập

| ID | Chỉ số | Định nghĩa | Ngưỡng | Ghi trong luận |
|----|--------|------------|--------|----------------|
| **P‑F1** | Macro-F1 thực thể (NER) | Trên tập **test cố định** (`train_ner.py` → `seqeval`, đồng bộ BIO / schema nhãn). Báo thêm precision/recall macro. | **> 96%** | Tên HF split hoặc file test, seed, phiên bản nhãn. |
| **P‑Acc** | Token accuracy (NER) | Tỉ lệ token gán đúng nhãn trên **cùng đúng tập với P‑F1**. | **> 96%** | Không dùng tập khác; không báo Acc cao trong khi F1 đo trên split khác. |

**Đạt Gate B về KPI khi:** `P‑F1 > 96%` **và** `P‑Acc > 96%`.

#### B.1.2 Bổ sung — báo cáo bắt buộc trong Chương thực nghiệm, **không gộp** vào Gate B primary

| ID | Chỉ số | Ghi chú |
|----|--------|--------|
| **S‑NER‑EM** | Exact Match chuỗi nhãn / span-level (định nghĩa trong Ch.5 luận) | Thường khó hơn F1 token; báo để reviewer hiểu chất lượng “chuỗi hoàn chỉnh”. |
| **S‑E2E** | Khớp chuẩn hóa end-to-end (pipeline → `address_standardized` vs tham chiếu) | **Không ép ngưỡng 96%** trừ khi có **phụ lục** thu hẹp phạm vi (ví dụ một tỉnh, một domain). Ngưỡng 96% chủ yếu cho **NER primary**. |
| **S‑RET** | Độ chính xác retrieval: ví dụ **Recall@k**, đúng top‑1 có metadata HC, cosine threshold — theo script `evaluate_retriever.py` / log `mgte_confidence_score` | Mô tả protocol riêng, **không thay P‑F1/P‑Acc**. |

**Artifacts:** Phiên bản model (`models/...`), `NER_MODEL_ID` / checksum, ngày train, và **CSV/HTML** báo cáo thực nghiệm (`experiment` trong `config.yaml`) lưu cùng kết quả số.

**Gate B:** **P‑F1**, **P‑Acc** đạt như **B.1.1** + regression PreLabeler (B.2) pass + B.3 khóa inference.

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
