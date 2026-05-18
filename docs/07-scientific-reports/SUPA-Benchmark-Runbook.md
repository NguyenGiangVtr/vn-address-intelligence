# SUPA-Bench — Runbook (demo & kiểm thử lặp lại)

**Mục tiêu:** Một trình tự lệnh có thể chạy **nhiều lần**, sinh artifact rõ ràng và cập nhật `vnai-supa-generated-metrics.tex` (đã `\input` trong `vnai-chapters-master.tex`).

**Quy tắc:** Không ghi `prq.ground_truth` — chỉ `SELECT` khi trích.

### Tránh lỗi khi copy lệnh (Windows PowerShell)

- Chỉ dán **một dòng** là đúng cú pháp — **không** dán prompt `PS D:\...>` cùng dòng lệnh.
- **Không** dán nguyên khối log lỗi (các dòng bắt đầu bằng `+`, `At line:`, `CategoryInfo`) — PowerShell coi đó là lệnh mới → lỗi `MissingArgument`, `Unexpected token`.
- **`psql` không có sẵn** trên nhiều máy Windows (chưa cài PostgreSQL client hoặc chưa thêm vào `PATH`). Dùng lệnh **Python** dưới mục 0 là đủ.

---

## 0. Một lần trên PostgreSQL (áp DDL)

**Khuyến nghị (không cần `psql`):** dùng kết nối trong `.env` giống ứng dụng (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME`).

```powershell
cd "D:\2.GIT SOURCE\vn-address-intelligence"
$env:PYTHONPATH = "."
python scripts/sql/apply_sql_file.py scripts/migration/20260209_prq_supa_benchmark_tables.sql
```

**Tuỳ chọn (nếu đã cài `psql` và có trong PATH):** mở **cmd** hoặc PowerShell, trỏ tới file SQL (cú pháp URL do `psql` quy định):

```text
psql "postgresql://USER:PASSWORD@HOST:5432/DBNAME" -f scripts/migration/20260209_prq_supa_benchmark_tables.sql
```

*(Trong PowerShell, biến môi trường dùng `$env:DATABASE_URL`; nhiều team không đặt `DATABASE_URL` mà chỉ có `.env` — nên ưu tiên lệnh `python scripts/sql/apply_sql_file.py` ở trên.)*

Biến kết nối phải trùng snapshot DB báo cáo.

---

## 1. Luồng tự động một lần gọi (khuyến nghị)

### A. Chỉ tạo cohort + xuất CSV (chưa có dự đoán)

Sau bước này, điền cột **`pred_standardized`** trong CSV (hoặc xuất file mới có cùng `specimen_id`). **Repo không tạo sẵn** `reports/supa_preds_filled.csv` — đó là **đầu ra** sau khi bạn chạy pipeline chuẩn hóa (hoặc file giả lập minh hoạ ở mục B / `make-demo-preds`).

```powershell
cd "D:\2.GIT SOURCE\vn-address-intelligence"
$env:PYTHONPATH=".;src"
# Mỗi lần chạy: cohort + nhiễu khác (rng_seed ngẫu nhiên, in stderr + lưu DB)
python scripts/experiments/supa_benchmark.py workflow --n 1000 `
  --specimens-out reports/supa_workflow_specimens_latest.csv
```

Cohort **cố định** cho báo cáo (tái lập): thêm `--seed 42` (hoặc số bạn chọn).

```powershell
python scripts/experiments/supa_benchmark.py workflow --n 1000 --seed 42 `
  --specimens-out reports/supa_workflow_specimens_latest.csv
```

Hoặc:

```powershell
.\scripts\experiments\run_supa_benchmark.ps1 -N 1000
.\scripts\experiments\run_supa_benchmark.ps1 -N 1000 -Seed 42
```

Hoặc bash:

```bash
cd /path/to/vn-address-intelligence
export PYTHONPATH=.:src
python scripts/experiments/supa_benchmark.py workflow --n 1000
python scripts/experiments/supa_benchmark.py workflow --n 1000 --seed 42
```

### B. Sau khi đã có file dự đoán — hoàn tất → báo cáo LaTeX

**Điều kiện:** file `--preds` phải **tồn tại** trên đĩa. Nếu chưa có pipeline thật, sinh một CSV tối giản (**chỉ** `specimen_id` + `pred_standardized`) bằng:

```powershell
python scripts/experiments/supa_benchmark.py make-demo-preds `
  --from reports/supa_workflow_specimens_latest.csv `
  --out reports/supa_preds_filled.csv
```

(`--column ref_address_v1` nếu muốn copy tham chiếu v1 thay cho v2.)

**Chạy end-to-end thật** (predictions do bạn cung cấp + provenance):

```powershell
python scripts/experiments/supa_benchmark.py workflow `
  --skip-extract `
  --run-id <RUN_ID_IN_LOG> `
  --preds reports/supa_preds_filled.csv `
  --source-note "config=app/ai/config.yaml; artifact=models/...; commit=$(git rev-parse --short HEAD)" `
  --specimens-out reports/supa_workflow_specimens_latest.csv
```

**Smoke test không dùng cho số báo cáo chính:** sao chép oracle `ref_address_v2` → `pred_standardized`, kỳ vọng EM\@v2 gần 100\% (kiểm tra kênh `import-preds` / `eval` / LaTeX). Không `--preds`; không `--source-note`.

```powershell
python scripts/experiments/supa_benchmark.py workflow `
  --skip-extract `
  --run-id <RUN_ID_IN_LOG> `
  --preds-demo-ref-v2 `
  --specimens-out reports/supa_workflow_specimens_latest.csv
```

`RUN_ID`: xem `reports/supa_benchmark_last_run_id.txt` sau bước A, hoặc bảng `prq.supa_benchmark_run`.

PowerShell shorthand:

```powershell
.\scripts\experiments\run_supa_benchmark.ps1 -SkipExtract -RunId 3 `
  -PredsCsv reports\supa_preds_filled.csv `
  -SourceNote "production_pipeline pilot; cfg=..."
```

### C. Biên dịch PDF (số SUPA vào các chương đã `\input`)

```powershell
cd docs\scientific-report
xelatex vnai-chapters-master.tex
xelatex vnai-chapters-master.tex
```

---

## 2. Từng bước thủ công (debug)

| Bước | Lệnh |
|------|------|
| Trích + nhiễu | `python scripts/experiments/supa_benchmark.py extract --n 10000` (seed auto) hoặc `… --seed 42` (cohort cố định) |
| Xuất CSV | `python scripts/experiments/supa_benchmark.py export-specimens --out reports/x.csv` |
| Minh hoạ CSV preds (oracle từ ref) | `python scripts/experiments/supa_benchmark.py make-demo-preds --from reports/supa_workflow_specimens_latest.csv --out reports/supa_preds_filled.csv` |
| Nhập dự đoán | `python scripts/experiments/supa_benchmark.py import-preds --csv reports/preds.csv --source-note "..."` |
| Đánh giá | `python scripts/experiments/supa_benchmark.py eval` |
| Sinh macro TeX | `python scripts/experiments/supa_benchmark.py export-tex` |

---

## 3. Artifact cần lưu khi báo cáo

| File | Ý nghĩa |
|------|---------|
| `reports/supa_benchmark_last_run_id.txt` | `run_id` mới nhất (extract) |
| `reports/supa_benchmark_last_metrics.json` | EM\@v2 / EM\@v1, `n_scored`, … |
| `reports/supa_benchmark_last_import_manifest.json` | Nguồn gốc `import-preds` |
| `reports/supa_benchmark_demo_preds_ref_v2.csv` | Chỉ khi `--preds-demo-ref-v2`: bản preds oracle (copy ref v2 — smoke, không chứng cứ model) |
| `docs/scientific-report/vnai-supa-generated-metrics.tex` | Macro `\VNASUPA*` cho PDF |

Nếu `n_scored = 0`, các macro `%` trong bảng Chương 5 là `---` — **đúng**, không điền tay.

---

## 4. Đồng bộ thêm `vnai-generated-metrics.tex` (NER + audit — tùy chọn)

Không chứa SUPA; chạy khi có `training_log.json` / audit JSON:

```powershell
python scripts/flow/generate_scientific_report_metrics.py `
  --training-log models/phobert-ner-vn-flow-last/training_log.json `
  --audit-json reports/audit_acq_admin_bridge_last.json
```

**Tham số script | ý nghĩa**

| Tham số | Ý nghĩa |
|---------|---------|
| `--training-log` | Đường dẫn `training_log.json` (sau `train_ner.py` hoặc artifact tương đương). Bỏ qua → macro NER là `---`. |
| `--audit-json` | Snapshot JSON từ `audit_acq_admin_bridge.py --write-json …`. Bỏ qua → các macro audit là `---`. |
| `--experiment-csv` | Tuỳ chọn: `\VNAIGENExperimentCsvNote` lấy hint từ hàng cuối CSV. |
| `--out` | Mặc định `docs/scientific-report/vnai-generated-metrics.tex`; ghi đè file TeX macro. |

**Macro LaTeX `\VNAIGEN…`:** trong PDF luận, xem Bảng có label `tab:vnaigen-macro-glossary` trong `vnai-chapter-05-experiments.tex`.

---

## 5. Thuật ngữ — ý nghĩa từng biến (runbook \& CLI)

### 5.1. Môi trường

| Biến / cài đặt | Ý nghĩa |
|----------------|---------|
| `PYTHONPATH="."` | Bắt buộc khi chạy Python từ **gốc repo** để `import app.*` và `scripts.*` resolve đúng. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` | Kết nối PostgreSQL (đọc từ `.env` bởi `apply_sql_file.py` và `supa_benchmark.py`). Snapshot này phải **trùng** snapshot báo cáo trong luận. |

### 5.2. Tham số `workflow` (`supa_benchmark.py workflow …`)

| Tham số | Ý nghĩa |
|---------|---------|
| `--n` | Số dòng **tối đa** muốn lấy mẫu từ `prq.ground_truth` (sau lọc `address` / `old_address` không rỗng). Thực tế có thể ít hơn nếu DB không đủ dòng thỏa điều kiện. **Lưu ý:** với subcommand **`workflow`**, nếu **không** truyền `--n` thì mặc định trong code hiện tại là **10000** (`supa_benchmark.py`); các ví dụ mục 1 dùng `--n 1000` chỉ là minh họa nhẹ. Subcommand **`extract`** bắt buộc có `--n`. |
| `--seed` | **Hạt giống** PRNG và thứ tự lấy mẫu (`ORDER BY md5(id||seed)`). **Bỏ qua** tham số này trên `extract` / `workflow` → mỗi lần gọi script chọn một `rng_seed` ngẫu nhiên (in ra stderr), cohort + nhiễu **khác nhau** giữa các lần chạy; giá trị vẫn được lưu trên `prq.supa_benchmark_run.rng_seed`. Truyền `--seed <int>` khi cần tái lập báo cáo. |
| `--noise-profile` | Mã phiên bản hàm nhiễu (vd. `SUP-1.0.0`). Ghi vào DB và báo cáo; đổi profile → cohort vẫn có thể giữ nhưng quy tắc làm xấu chuỗi khác. |
| `--notes` | Chuỗi ghi chú tự do lưu trên `prq.supa_benchmark_run.notes` (vd. “demo 2026-02”, mã ticket). |
| `--specimens-out` | Đường dẫn file **CSV** xuất danh sách mẫu để bạn chạy chuẩn hóa bên ngoài. |
| `--preds` | CSV **sau** bước chuẩn hóa: phải có cột dự đoán (`pred_standardized` hoặc tên alias được script chấp nhận) + khóa `specimen_id` hoặc (`run_id`,`local_idx`). **Đường dẫn phải trỏ tới file thật** — nếu thiếu, script in gợi ý `make-demo-preds` hoặc `--preds-demo-ref-v2`. |
| `--preds-demo-ref-v2` | **Loại trừ** với `--preds`. Sau `export-specimens`, tạo `reports/supa_benchmark_demo_preds_ref_v2.csv` bằng cách copy cột `ref_address_v2` → `pred_standardized` (oracle / smoke runbook; `source_note` cố định trong mã). |
| `--source-note` | **Bắt buộc** khi có `--preds`: mô tả nguồn gốc khoa học (config, checkpoint, commit, GPU…) — lưu vào `supa_benchmark_last_import_manifest.json`. **Không dùng** khi chỉ có `--preds-demo-ref-v2`. |
| `--skip-extract` | Bỏ bước trích mới; dùng `--run-id` (hoặc run **mới nhất** trong DB) cho export / import / eval. |
| `--run-id` | Khóa `prq.supa_benchmark_run.id` của **một lần** chạy extract; dùng khi hoàn tất preds cho đúng cohort (không lẫn run khác). |

#### 5.2.2. Quy tắc làm nhiễu (apply_noise)

Hàm `apply_noise` được thiết kế để giả lập thói quen gõ địa chỉ thực tế của người dùng Việt Nam. Hệ thống cung cấp hai cấp độ nhiễu chính:

| Đặc điểm | **SUP-1.0.0** (Default) | **SUP-D2-1.0.0** (High Noise) |
| :--- | :--- | :--- |
| **Dấu tiếng Việt** | Giữ nguyên (chỉ lỗi gõ nhẹ) | **Loại bỏ hoàn toàn dấu** (Unaccented) |
| **Viết tắt (Admin)** | Xác suất 65% | Xác suất **90%** (Gần như luôn viết tắt) |
| **Lỗi ký tự (Typos)** | Lỗi IME cơ bản (15%) | **Nặng**: Hoán đổi ký tự (50%) + Lặp ký tự (30%) |
| **Cấu trúc (Prefix)** | Xác suất 40% | Xác suất **60%** (Tầng trệt, Cạnh, Phía sau...) |
| **Dấu câu & Space** | Thêm khoảng trắng quanh dấu phẩy | **Xóa khoảng trắng sau dấu phẩy**, Triple spacing |
| **Vùng miền (Slang)** | Xác suất 30% | Xác suất **60%** |

**Chi tiết các loại nhiễu:**

- **Viết tắt hành chính:**
    - Thay thế `Phường`, `Quận`, `Huyện`, `Thành phố`, `Đường` bằng các biến thể như `P.`, `Q.`, `H.`, `TP.`, `Đ.` hoặc viết thường, bỏ dấu chấm.
    - Giả lập thói quen viết liền: `Q1`, `P12`, `Q.BT` (Bình Thạnh).
- **Biến thể vùng miền & Ký tự đặc biệt:**
    - Hoán đổi giữa `Ngõ/Ngách` (miền Bắc) và `Hẻm/Kiệt` (miền Trung/Nam).
    - Biến đổi dấu `/` thành ` sẹc `, ` sec `, `-` hoặc thay đổi khoảng trắng xung quanh.
- **Lỗi bộ gõ (IME Errors - Telex/VNI):**
    - Giả lập lỗi gõ nhanh/dính phím: `đ` -> `dđ`, `đd`; `â` -> `aâ`.
    - Lỗi sai vị trí dấu do bảng mã/font (vd: `Hòa` thành `Hoà`).
    - Ngẫu nhiên mất dấu ở một từ bất kỳ trong chuỗi (do gõ nhanh).
- **Nhiễu cấu trúc & Case:**
    - Thêm tiền tố/hậu tố vị trí: `Chỗ`, `Ngay`, `Gần`, `Cạnh`, `Đối diện`, `Sau lưng`, `Tòa nhà`, `Chung cư`, `Tầng`.
    - Ngẫu nhiên chuyển toàn bộ chuỗi sang `VIẾT HOA` hoặc `viết thường`.

Các quy tắc này giúp tập dữ liệu SUPA-Bench phản ánh đúng độ phức tạp của dữ liệu thực tế mà hệ thống AI cần xử lý.

#### 5.2.3. Ablation Study (Nghiên cứu cắt bỏ)

Để đánh giá đóng góp của từng thành phần trong Pipeline Hybrid, bạn có thể chạy `production_pipeline.py` với các cờ (flags) để bật/tắt các mô hình:

- `--no-ner`: Bỏ qua bước trích xuất thực thể (PhoBERT NER).
- `--no-retrieval`: Bỏ qua bước truy hồi ứng viên (Siamese).
- `--no-llm`: Bỏ qua bước tinh chỉnh bằng Qwen3 (kết quả lấy trực tiếp từ retrieval).
- `--retriever-type <mgte|phobert>`: Thay đổi mô hình backbone cho retrieval.

**Ví dụ chạy thực nghiệm:**

1. **Full Hybrid (SOTA):**
   `python src/app/ai/production_pipeline.py --limit 1000`
2. **Chỉ dùng Retrieval (mGTE):**
   `python src/app/ai/production_pipeline.py --no-ner --no-llm --retriever-type mgte`
3. **Chỉ dùng LLM (Không ngữ cảnh):**
   `python src/app/ai/production_pipeline.py --no-ner --no-retrieval`

Kết quả sẽ được ghi vào cột `processing_method` với các tag tương ứng (ví dụ: `HYBRID_NER_MGTE_LLM`) để dễ dàng phân tích trong bước `eval` của SUPA-Bench.

#### 5.2.1. `--seed` — cố định cohort vs. mặc định ngẫu nhiên mỗi lần chạy

Từ phiên bản hiện tại của `supa_benchmark.py`: nếu **không** truyền `--seed` trên `extract` hoặc `workflow`, script sinh **`rng_seed` ngẫu nhiên** (31 bit, `secrets`) để **mỗi lần chạy** (mỗi invocation) có cohort và nhiễu tổng hợp khác nhau trừ khi trùng hạ cực hiếm; seed được in ra **stderr** và ghi vào DB. Để luận văn / tái lập khoa học, luôn truyền `--seed <int>` và ghi số đó trong phụ lục.

**`42` không phải hằng số “chuẩn khoa học”** — chỉ là một **số nguyên** bạn chọn khi cần cohort cố định (thường dùng trong tài liệu ML minh hoạ; mọi giá trị như `7`, `12345`, `20260209` đều hợp lệ). Điều quan trọng là **ghi rõ seed đã dùng** trong luận / phụ lục cùng `N` và profile nhiễu.

**Seed điều khiển hai việc trong pipeline SUPA:**

1. **Chọn tập mẫu từ `prq.ground_truth`** — truy vấn sắp xếp cố định theo \( \text{md5}(\texttt{id} \,\|\, \texttt{seed}) \) rồi lấy `LIMIT N`. Cùng DB, cùng \(N\), cùng seed → **cùng danh sách `ground_truth_id`**.
2. **Làm nhiễu tổng hợp** — bên Python dùng `random.Random(seed)`: cùng seed → **cùng chuỗi quyết định** (có/không tiền tố, khoảng trắng thừa…) trên lộ trình các mẫu.

**Nên cố định hay ngẫu nhiên?**

| Mục đích | Khuyến nghị |
|----------|-------------|
| Báo cáo chính, luận, bài báo (**tái lập được**) | **Cố định một seed** (vd. `--seed 42` hoặc số có ý nghĩa nội bộ); không đổi giữa các lần chạy báo cáo cuối. |
| Thử demo nhanh, so sánh pipeline | Giữ seed cố định để so sánh công bằng giữa hai phiên bản model **trên cùng cohort + cùng nhiễu**. |
| Đánh giá **độ phân tán** (nhiều cohort ngẫu nhiên) | Bỏ `--seed` trên từng lần `extract`/`workflow` (seed auto + lưu DB) **hoặc** dùng `replicate --mode sweep-seed` không truyền `--seed-start` (base ngẫu nhiên mỗi lần gọi script); hoặc chọn dãy seed có chủ đích (`101`, `102`, …) và báo **trung bình / khoảng**. |
| Chỉ khám phá nội bộ | Có thể chọn seed tùy ý miễn **ghi trong `supa_benchmark_run`/runbook**; tránh báo “tái lập chính xác” nếu không ghi nhận. |

**Không nên:** dùng seed ngẫu nhiên rồi **không lưu** `rng_seed` (DB đã lưu khi extract — an toàn); tránh báo “tái lập chính xác” trong luận nếu không ghi `rng_seed` và snapshot DB.

**Tóm lắng:** Cho luận văn chính: chọn **một số nguyên**, truyền `--seed`, ghi \(\texttt{seed}\) vào macro `\VNASUPASeed`/JSON run. Cho thử nhanh mỗi cohort khác: **không** truyền `--seed`, copy `rng_seed` từ stderr hoặc từ DB nếu sau này cần tái chạy.

### 5.3. Script PowerShell `run_supa_benchmark.ps1`

| Tham số | Tương đương |
|---------|--------------|
| `-N` | `--n` |
| `-Seed` | `--seed` (bỏ `-Seed` → cohort ngẫu nhiên mỗi lần) |
| `-NoiseProfile` | `--noise-profile` |
| `-SkipExtract` | `--skip-extract` |
| `-RunId` | `--run-id` (chỉ khi `-SkipExtract`) |
| `-PredsCsv` | `--preds` |
| `-SourceNote` | `--source-note` (bắt buộc nếu có `-PredsCsv`) |
| `-DemoPredsCopyRef` | `--preds-demo-ref-v2` (không kết hợp `-PredsCsv`) |
| `-SpecimensOut` | `--specimens-out` |

### 5.4. Bash (`run_supa_benchmark.sh`)

| Biến môi trường | Mặc định | Ý nghĩa |
|------------------|----------|---------|
| `N` | 1000 | Cỡ mẫu (`--n`) |
| `SEED` | 42 | Hạt giống |
| `NOISE_PROFILE` | `SUP-1.0.0` | Profile nhiễu |
| `SPECIMENS_OUT` | `reports/supa_workflow_specimens_latest.csv` | CSV xuất |
| `SKIP_EXTRACT` | 0 → đặt `1` để bật `--skip-extract` | |
| `RUN_ID` | (trống) | `--run-id` khi skip extract |
| `PREDS_CSV` | (trống) | `--preds` |
| `SOURCE_NOTE` | (trống) | Bắt buộc nếu đặt `PREDS_CSV` |
| `DEMO_PREDS_REF_V2` | `0` | Đặt `1` để thêm `--preds-demo-ref-v2` (**không** đặt kèm `PREDS_CSV`) |

### 5.5. Cột CSV chuẩn (xuất `export-specimens`)

| Cột | Ý nghĩa |
|-----|---------|
| `specimen_id` | Khóa chính dòng trong `prq.supa_benchmark_specimen.id` — dùng khớp khi `import-preds`. |
| `run_id` | Thuộc lần chạy cohort nào. |
| `local_idx` | Thứ tự trong run (1…N); có thể dùng kết hợp `run_id` thay `specimen_id`. |
| `ground_truth_id` | Khóa bản ghi **nguồn** trong `prq.ground_truth` (chỉ đọc khi trích; không sửa bảng gốc). |
| `noisy_raw_address` | Đầu vào đã làm **nhiễu tổng hợp** đưa vào pipeline chuẩn hóa. |
| `ref_address_v2` | Chuỗi tham chiếu **chuẩn v2** (copy `address` lúc trích) — mục tiêu EM\@v2. |
| `ref_address_v1` | Chuỗi tham chiếu **v1 / trước cải cách** (`old_address`) — mục tiêu EM\@v1. |
| `pred_standardized` | **Đầu ra** của bước chuẩn hóa; để trống khi export, điền trước `import-preds`. |

### 5.6. JSON `reports/supa_benchmark_last_metrics.json`

| Khóa | Ý nghĩa |
|------|---------|
| `run_id` | Run được đánh giá. |
| `n_requested` | Tham số `--n` lúc extract. |
| `n_realized` | Số dòng specimen thực Insert (sau lọc GT). |
| `n_specimens_table` | Số hàng specimen của `run_id` trong DB. |
| `n_scored` | Số specimen có `pred_standardized` **không rỗng** — chỉ trên tập này mới tính EM. |
| `em_v2_pct` | Tỉ lệ phần trăm (0–100) exact-match: `normalize(pred)==normalize(ref_address_v2)`. `null` nếu `n_scored=0`. |
| `em_v1_pct` | Giống trên nhưng so `ref_address_v1`. |
| `rng_seed`, `noise_profile_id`, `git_commit` | Tái lập cohort \& mã phục vụ báo cáo. |
| `note` | Mô tả ngắn quy tắc so khớp (NFC, gom space). |

### 5.7. JSON manifest import (`reports/supa_benchmark_last_import_manifest.json`)

| Khóa | Ý nghĩa |
|------|---------|
| `csv_path` | File preds đã nạp. |
| `rows_read` / `rows_updated` | Số dòng CSV đọc / số UPDATE thành công (mỗi dòng có pred không rỗng). |
| `source_note` | Chuỗi provenance **bạn nhập**. |
| `git_commit_at_import` | Commit repo lúc import (auto). |
| `errors` | Lỗi parse từng dòng (nếu có). |

### 5.8. Liên kết LaTeX

Mọi macro `\VNASUPA…` trong `vnai-supa-generated-metrics.tex` được **ghi đè** bởi `export-tex` từ JSON metrics. Ý nghĩa từng macro được trình bày trong **Chương 5** (mục SUPA-Bench): bảng thuật ngữ macro ngay sau ``tab:supa-bench`` trong `vnai-chapter-05-experiments.tex`.

### 5.9. Lặp lại nhiều lần (`replicate`), metric theo `run_id`, retention

- **Subcommand:** `python scripts/experiments/supa_benchmark.py replicate …` — lặp `extract → export-specimens → [import-preds] → eval` với `--n-runs` và `--mode sweep-seed` (seed `base`, `base+1`, …; **bỏ** `--seed-start` → `base` ngẫu nhiên mỗi lần gọi script) hoặc `--mode repeat-determinism` (cùng `--seed`, mặc định 42). Cờ `--retention N` giữ **N** run mới nhất trong `prq.supa_benchmark_run` và xóa các run cũ hơn (CASCADE specimen).
- **Artifact theo run:** sau mỗi `eval`, ghi `reports/supa_metrics_run_{run_id}.json` và (nếu đã áp migration) cột `prq.supa_benchmark_run.eval_metrics_json`.
- **DDL bổ sung:** `python scripts/sql/apply_sql_file.py scripts/migration/20260512_retrieval_eval_and_supa_metrics.sql` (cột JSONB + bảng `ath.retrieval_eval_run` cho đo retrieval).
- **Script bọc:** `scripts/experiments/run_supa_replicate.ps1` và `scripts/experiments/run_supa_replicate.sh` (mặc định 20 lần, sweep-seed, oracle demo — chỉ smoke).
- **Tổng hợp batch:** `aggregate-runs` (tùy `--min-run-id` + `--max-run-id`, hoặc `--from-batch-json reports/supa_benchmark_last_batch_range.json` sau `replicate`) sinh JSON + Markdown; mặc định `reports/supa_benchmark_aggregate_last.json` và `.md`. Thêm `--persist-ath` để `INSERT` vào `ath.supa_stratified_eval_summary` (cần migration 20260513).

### 5.10. Cohort phân tầng (`extract-stratified`, `replicate-stratified`)

- **DDL:** `python scripts/sql/apply_sql_file.py scripts/migration/20260513_supa_stratified_specimen_and_ath_summary.sql` (cột `stratum_code`, `latitude`, `longitude`, `latency_ms` trên `prq.supa_benchmark_specimen`; bảng `ath.supa_stratified_eval_summary`).
- **Một lần trích:** `python scripts/experiments/supa_benchmark.py extract-stratified --n 2000 --seed 42 --strat-version strat-v1`
- **K lần độc lập (ví dụ K=5):** `python scripts/experiments/supa_benchmark.py replicate-stratified --k-runs 5 --n 2000 --base-seed 42 --preds-demo-ref-v2` (hoặc `--preds` + `--source-note`). Sau đó: `aggregate-runs --from-batch-json reports/supa_benchmark_last_batch_range.json --persist-ath --methodology-version strat-v1`
- **Script bọc:** `scripts/experiments/run_supa_replicate_stratified.ps1` · `bash scripts/experiments/run_supa_replicate_stratified.sh -- …`
- **Import preds:** cột tùy chọn `latency_ms` (mỗi specimen) để `eval` tính mean/P95/throughput.
- **Chi tiết stratum / ngưỡng:** xem `VNAI-he-thong-thuc-hien-tong-hop.md` mục 9.5.1.

---

## 6. Bash env vars (tuỳ chọn)

```bash
SKIP_EXTRACT=1 RUN_ID=5 PREDS_CSV=reports/p.csv SOURCE_NOTE="..." \
  bash scripts/experiments/run_supa_benchmark.sh
```

---

*Đặc tả đầy đủ:* `Protocol-Synthetic-User-Perturbation-Benchmark-Google-Ground-Truth.md`

---

## 7. Chỉ mục mục

| § | Nội dung |
|---|----------|
| 0 | DDL / áp bảng |
| 1 | Luồng `workflow` |
| 2 | Lệnh từng bước |
| 3 | Artifact báo cáo |
| 4 | `vnai-generated-metrics` (NER/audit — không SUPA) |
| 5 | **Thuật ngữ biến** (CLI, CSV, JSON, LaTeX) — gồm §5.9 replicate / retention và §5.10 stratified |
| 6 | Bash |
| 7 | Chỉ mục § |
