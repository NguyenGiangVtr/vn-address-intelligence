# Scientific report (LaTeX) — VNAI

## Mục đích

Thư mục này chứa phần **Chương 4–6** (thiết kế, thực nghiệm, kết luận) viết dưới dạng báo cáo nghiên cứu; nội dung phải **bám thực nghiệm** và **có thể đối chiếu** với mã nguồn trong repo.

## Luồng một lần chạy (repo)

Sau khi cấu hình DB và (tuỳ) HF, dùng orchestrator ở `scripts/flow/` để: regression → audit (JSON) → `experiment_runner` → `production_pipeline` pilot → NER smoke → **`generate_scientific_report_metrics.py`** cập nhật **`vnai-generated-metrics.tex`**.

- Chi tiết: [`scripts/flow/README.md`](../../scripts/flow/README.md)

## Nguyên tắc minh chứng (bắt buộc)

1. **Số liệu từ DB / audit:** chỉ ghi sau khi đã chạy script tương ứng; trong LaTeX nêu rõ lệnh (ví dụ `python scripts/diagnostics/audit_acq_admin_bridge.py --write-json ...`) và **thời điểm** hoặc **hash commit** nếu cần trích dẫn trong luận.
2. **Số liệu mô hình (F1, Acc, …):** đồng bộ từ `training_log.json` / CSV thực nghiệm qua generator — **không** bịa đặt hoặc ước lượng tay trong `.tex` chính.
3. **Tách bạch:** *mục tiêu ngưỡng* (Gate B P---F1 / P---Acc) khác *kết quả đo được*; audit bridge là **quan sát schema/lineage** trên queue, không thay thế báo cáo huấn luyện NER đầy đủ.

## Biên dịch

```powershell
cd "docs/scientific-report"
xelatex vnai-chapters-master.tex
xelatex vnai-chapters-master.tex
```

(XeLaTeX khuyến nghị vì `\usepackage{fontspec}` + tiếng Việt.)

## Tệp chính

| Tệp | Vai trò |
|-----|--------|
| `vnai-chapters-master.tex` | File tổng, abstract, bibliography mẫu |
| `vnai-chapter-04-design.tex` | Chương 4 — yêu cầu & kiến trúc |
| `vnai-chapter-05-experiments.tex` | Chương 5 — chỉ số + audit + bảng đồng bộ artifact |
| `vnai-chapter-06-conclusion.tex` | Chương 6 — kết luận, hạn chế có căn cứ đo được |
| **`vnai-generated-metrics.tex`** | **Sinh tự động** — macro từ `training_log.json` + JSON audit; không chỉnh tay |
