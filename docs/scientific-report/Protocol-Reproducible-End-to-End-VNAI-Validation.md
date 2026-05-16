# Protocol: Reproducible End-to-End VNAI Validation and Reporting

**Document type:** Experimental / engineering reproducibility protocol (có thể đính kèm báo cáo khoa học dưới dạng *Supplementary Protocol*, *Materials and Methods — Computational Reproducibility*, hoặc *Standard Operating Procedure — SOP* cho luồng phần mềm).

**Synonyms (ngữ cảnh khác nhau):** *playbook* (vận hành), *runbook* (triển khai), *validation protocol* (thử nghiệm có kiểm soát). Trong văn bản học thuật, **protocol** là tên ưu tiên.

**Version:** 1.0  
**Scope:** Luồng tương đương `scripts/flow/run_full_vnai_flow.ps1` (hoặc `.sh`), tách từng bước, tiêu chí pass/fail, và hành động khắc phục.

---

## 1. Mục đích và phạm vi

**Mục đích:** Mô tả trình tự lệnh, kết quả mong đợi, và quy tắc *có được phép chuyển bước hay không* khi xác minh hệ thống VNAI (kiểm tra tĩnh, tương tác cơ sở dữ liệu, pipeline thử nghiệm, huấn luyện NER smoke, sinh số liệu cho LaTeX).

**Phạm vi:** Môi trường Windows PowerShell (lệnh dưới đây dùng cú pháp PowerShell). Linux/macOS: thay `.\scripts\...` bằng `./scripts/...` và biến môi trường tương đương.

**Không nằm trong phạm vi:** Huấn luyện production đầy đủ; tối ưu siêu tham số; đánh giá mô hình trên toàn bộ tập dữ liệu nội bộ (trừ khi được định nghĩa thêm trong nghiên cứu riêng).

---

## 2. Định nghĩa Pass / Fail (áp dụng chung)

| Khái niệm | Định nghĩa vận hành |
|-----------|----------------------|
| **Pass** | Tiến trình kết thúc với **mã thoát 0** (`$LASTEXITCODE -eq 0` trong PowerShell sau lệnh gọi trực tiếp; hoặc không có ngoại lệ khi chạy script). Đầu ra có thể chứa cảnh báo (warning) nhưng không được báo lỗi dừng bước. |
| **Fail** | Mã thoát khác 0, traceback Python, hoặc script PowerShell `throw`. |
| **Cảnh báo (WARN)** | Mã thoát 0 nhưng nội dung cho biết bỏ qua bước tùy chọn (ví dụ `-OptionalDb`). Bước được coi là *hoàn thành theo chế độ đã chọn*, không tương đương pass đầy đủ của toàn bộ luồng DB. |

**Quy tắc chuyển bước (tóm tắt):**

- Fail ở bước **bắt buộc** (§3.1–3.3): **không** chuyển sang bước phụ thuộc; khắc phục rồi chạy lại từ bước fail (hoặc từ đầu nếu trạng thái không rõ).
- Fail ở bước **audit DB** (§4): **không** chạy §5–§6 trừ khi dùng chế độ `-OptionalDb` / `-SkipDb` (khi đó ghi rõ trong báo cáo là *partial protocol*).
- Fail ở **train NER** (§7): vẫn có thể chạy §8 nếu đã có `training_log.json` hợp lệ từ lần trước; nếu không, §8 sẽ thiếu số NER (generator vẫn có thể chạy nhưng giá trị NER có thể là placeholder — xem §8).

---

## 3. Chuẩn bị môi trường (bước 0 — bắt buộc trước mọi bước sau)

### 3.1. Lệnh

```powershell
cd "D:\2.GIT SOURCE\vn-address-intelligence"
$env:PYTHONPATH = "."
```

*(Điều chỉnh đường dẫn `cd` theo máy thực tế.)*

### 3.2. Kết quả mong muốn (Pass)

- Lệnh `cd` không báo lỗi.
- `$env:PYTHONPATH` bằng `"."` sau khi gán.

### 3.3. Fail — xử lý

| Hiện tượng | Hành động | Đi tiếp? |
|-------------|-----------|----------|
| Không tìm thấy thư mục repo | Kiểm tra đường dẫn clone | **Không** |
| Không có `python` | Cài Python 3.11+ và PATH | **Không** |

---

## 4. Giai đoạn A — Kiểm tra tĩnh và hồi quy PreLabeler

### Bước A1 — `py_compile` các module then chốt

**Lệnh:**

```powershell
python -m py_compile `
  scripts/diagnostics/audit_acq_admin_bridge.py `
  scripts/flow/generate_scientific_report_metrics.py `
  app/ai/train_ner.py `
  app/ai/production_pipeline.py `
  app/ai/experiment_runner.py `
  app/ai/report_generator.py
```

**Pass:** Không in traceback; `$LASTEXITCODE` (nếu kiểm tra) là `0`; không file `.pyc` báo lỗi cú pháp.

**Fail:** `SyntaxError` hoặc `Error` kèm tên file — sửa mã nguồn Python tương ứng.

**Đi tiếp?** **Không**, cho đến khi A1 pass.

---

### Bước A2 — Bộ ca kiểm thử gán nhãn PreLabeler (rule-based)

**Lệnh:**

```powershell
python scripts/labeling/run_prelabeler_labeling_cases.py
```

**Pass:** Dòng cuối dạng `Result: N/N passed (100.0%)` với `N` bằng kích thước bộ JSON trong `scripts/labeling/prelabeler_labeling_cases.json` (ví dụ 330/330).

**Fail:** Bất kỳ `[FAIL]` hoặc tỷ lệ pass &lt; 100% theo ngưỡng script.

**Đi tiếp?** **Không** — cập nhật `PreLabeler` / service chia sẻ hoặc bộ case theo quy tắc dự án (xem `.cursor/rules/prelabeler-single-source.mdc`).

---

### Bước A3 — Hồi quy PreLabeler nhanh

**Lệnh:**

```powershell
python scripts/test/test_prelabeler_regression.py
```

**Pass:** Dòng chứa `OK` (theo convention script in `print("OK - ...")`).

**Fail:** AssertionError hoặc exit code ≠ 0.

**Đi tiếp?** **Không**.

---

## 5. Giai đoạn B — Kiểm tra cầu nối dữ liệu (audit, có PostgreSQL)

### Bước B1 — Audit + xuất JSON

**Lệnh:**

```powershell
python scripts/diagnostics/audit_acq_admin_bridge.py --write-json reports/audit_acq_admin_bridge_last.json
# Giao diện console tiếng Việt (snapshot JSON vẫn dùng chú thích tiếng Anh trong một số trường):
python scripts/diagnostics/audit_acq_admin_bridge.py --write-json reports/audit_acq_admin_bridge_last.json --lang vi
```

**Ghi chú kết quả:** Truy vấn `denorm_version_tuple_histogram_ambiguous_join` nhóm theo bộ `(admin_version tỉnh, huyện, xã)`. Một dòng queue có thể khớp **nhiều** bản ghi `mat` khác `admin_version`, nên **tổng các bucket có thể lớn hơn** tổng số dòng queue; đó là hành vi SQL mong đợi, không phải lỗi cộng dồn dữ liệu.

**Pass:** Script kết thúc 0; tệp `reports/audit_acq_admin_bridge_last.json` tồn tại và là JSON hợp lệ.

**Fail thường gặp:**

| Hiện tượng | Nguyên nhân điển hình | Hành động | Đi tiếp tới §6? |
|------------|------------------------|-----------|------------------|
| `Connection refused` | PostgreSQL tắt, sai host/port, chưa VPN | Bật DB / sửa `.env` / VPN | **Chỉ khi** dùng `-OptionalDb` hoặc `-SkipDb` trong script tổng; **không** nếu cần báo cáo đầy đủ DB |
| Timeout / authentication | Sai user/password | Sửa credential | **Không** cho đến khi pass |
| Lỗi logic SQL / schema | Lệch migration | Sửa DB hoặc script audit | **Không** |

**Ghi chép khoa học:** Nếu bỏ qua B1, ghi trong phụ lục: *Database audit was skipped (connectivity); downstream metrics exclude live DB audit snapshot.*

---

## 6. Giai đoạn C — Thực nghiệm không LLM (`experiment_runner`)

**Điều kiện tiên quyết:** B1 **Pass** (hoặc bạn chấp nhận báo cáo một phần và **không** chạy bước này).

**Lệnh:**

```powershell
python -m app.ai.experiment_runner --config app/ai/config.yaml --no-llm
```

**Pass:** Exit 0; thường có cập nhật `reports/experiment_results.csv` (hoặc artifact cấu hình quy định — đối chiếu `config.yaml`).

**Fail:** Đọc traceback; kiểm tra DB, quota đĩa, và `app/ai/config.yaml`.

**Đi tiếp?** **Không** nếu mục tiêu là luồng đầy đủ có thực nghiệm; có thể **có** nếu chỉ cần pipeline pilot sau khi sửa lỗi.

**Rủi ro dữ liệu:** Thực nghiệm có thể ghi kết quả vào DB hoặc file tùy cấu hình — sau fail nên dọn artifact và xem xét rollback DB (xem §11).

---

## 7. Giai đoạn D — Pipeline production (pilot, giới hạn bản ghi)

**Điều kiện tiên quyết:** B1 pass; khuyến nghị C pass.

**Lệnh (ví dụ 25 bản ghi):**

```powershell
python app/ai/production_pipeline.py --config app/ai/config.yaml --limit 25
```

**Pass:** Exit 0; log không dừng sớm với lỗi hàng loạt.

**Fail:** Lỗi mô hình (thiếu file weights), lỗi DB, OOM GPU/RAM.

**Đi tiếp?** Tùy mục tiêu: train NER (§8) **độc lập** với pilot DB; nhưng báo cáo metrics (§9) có thể cần `experiment_results.csv` và audit JSON.

**Rủi ro dữ liệu:** Pipeline cập nhật các cột trạng thái trên bảng queue trong `config` (thường `prq.address_cleansing_queue`). **Fail sau khi đã ghi một phần:** cần chiến lược restore từ backup hoặc cập nhật ngược theo id — không tự động trong repo.

---

## 8. Giai đoạn E — Huấn luyện NER smoke (Hugging Face + PyTorch)

**Lệnh:**

```powershell
python app/ai/train_ner.py `
  --hf-dataset dathuynh1108/ner-address-standard-dataset `
  --hf-max-train 4000 `
  --hf-max-eval 800 `
  --epochs 1 `
  --batch-size 8 `
  --output models/phobert-ner-vn-flow-last
```

**Pass:** Exit 0; tồn tại `models/phobert-ner-vn-flow-last/training_log.json` có khóa `eval_results` (hoặc tương đương script ghi).

**Fail:** Lỗi mạng (tải dataset), thiếu `torch`, OOM.

**Đi tiếp?** Có thể **có** sang §9 nếu đã có `training_log.json` từ lần chạy trước **và** bạn chấp nhận số liệu không đồng bộ với lần audit hiện tại; nếu không, **không** — chạy lại E sau khi khắc phục hoặc dùng `-SkipTrain` trong script tổng và ghi chú trong báo cáo.

**Thời gian:** Có thể rất lâu (nhiều phút đến hơn một giờ tùy máy).

---

## 9. Giai đoạn F — Sinh chỉ số LaTeX (`vnai-generated-metrics.tex`)

**Lệnh (đủ artifact):**

```powershell
python scripts/flow/generate_scientific_report_metrics.py `
  --training-log models/phobert-ner-vn-flow-last/training_log.json `
  --audit-json reports/audit_acq_admin_bridge_last.json `
  --experiment-csv reports/experiment_results.csv
```

**Pass:** Exit 0; dòng kiểu `Wrote .../vnai-generated-metrics.tex`; tệp đích được cập nhật thời gian sửa.

**Fail:** Thiếu đường dẫn đầu vào — bỏ tham số tương ứng **chỉ khi** chấp nhận placeholder trong TeX (xem code generator).

**Đi tiếp?** **Có** — biên dịch LaTeX (§10) nếu §9 pass hoặc nếu chấp nhận bản metrics thiếu mục.

---

## 10. Giai đoạn G — Biên dịch báo cáo (tuỳ chọn)

```powershell
cd docs\scientific-report
xelatex vnai-chapters-master.tex
xelatex vnai-chapters-master.tex
```

**Pass:** PDF sinh ra không lỗi fatal; cross-reference ổn định sau hai lần chạy.

**Fail:** Thiếu gói LaTeX — cài TeX distribution đầy đủ.

---

## 11. Khắc phục sau Fail — dọn cục bộ và cơ sở dữ liệu

### 11.1. Artifact phần mềm (an toàn khi xoá nếu không cần giữ)

```powershell
Remove-Item -Force -ErrorAction SilentlyContinue `
  reports\audit_acq_admin_bridge_last.json, `
  reports\experiment_results.csv
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
  models\phobert-ner-vn-flow-last
```

**Metrics đã ghi đè:** hoàn tác bằng Git nếu cần:

```powershell
git checkout -- docs/scientific-report/vnai-generated-metrics.tex
```

### 11.2. Cơ sở dữ liệu

- **Chỉ audit:** thường không ghi bảng nghiệp vụ; không cần rollback queue.
- **Đã chạy pipeline pilot:** xem xét restore từ snapshot / `pg_dump` thực hiện **trước** §7, hoặc cập nhật ngược theo chính sách DBA.
- **Bảng backup / snapshot** (`*_backup_*`, `mat.*_old`, v.v.): sau khi **xác nhận** không cần rollback, có thể `DROP TABLE ... CASCADE` từng bảng (liệt kê trước bằng truy vấn `information_schema` / `pg_tables` — không dùng wildcard `DROP` mù).

### 11.3. Tối ưu sau khi xoá bảng lớn (khuyến nghị DBA)

Chạy `VACUUM (ANALYZE)` trên schema liên quan hoặc theo lịch bảo trì cụm.

---

## 12. Ánh xạ một lệnh tổng (tùy chọn)

| Mục tiêu | Lệnh |
|----------|------|
| Toàn bộ mặc định (DB bắt buộc) | `.\scripts\flow\run_full_vnai_flow.ps1` |
| DB lỗi mạng nhưng vẫn train + metrics | `.\scripts\flow\run_full_vnai_flow.ps1 -OptionalDb` |
| Không gọi DB | `.\scripts\flow\run_full_vnai_flow.ps1 -SkipDb` |
| Bỏ train | `.\scripts\flow\run_full_vnai_flow.ps1 -SkipTrain` |

Script tổng phải kết thúc **exit code 0** để coi là *pass toàn trình một lần chạy*.

---

## 13. Trích dẫn gợi ý trong báo cáo khoa học

Ví dụ (tiếng Việt):

> *Quy trình tái lập được mô tả trong Phụ lục — **Protocol for Reproducible End-to-End VNAI Validation** (Phiên bản 1.0). Mỗi giai đoạn có tiêu chí hoàn thành nhị phân (pass/fail) và điều kiện tiên quyết rõ ràng giữa kiểm tra tĩnh, audit cơ sở dữ liệu, thực nghiệm, pipeline pilot, huấn luyện NER smoke, và sinh chỉ số LaTeX.*

---

## 14. Liên kết nội bộ

- Script tổng: `scripts/flow/run_full_vnai_flow.ps1`, `scripts/flow/run_full_vnai_flow.sh`
- Mô tả ngắn: `scripts/flow/README.md`
- Quy tắc PreLabeler (A2/A3): `.cursor/rules/prelabeler-single-source.mdc`

---

*Tài liệu này là **protocol** (ghi nhận quy trình có thể lặp lại và kiểm chứng), không thay thế mô tả phương pháp học thuật định tính trong chính văn bản chính.*
