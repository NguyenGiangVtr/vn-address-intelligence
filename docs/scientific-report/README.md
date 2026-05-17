# Scientific Report — VNAI

## 📁 Cấu trúc thư mục

```
docs/scientific-report/
├── mis-DATN-2026/          # 📘 LaTeX Thesis (Luận văn chính thức)
│   ├── chapters/           # Các chương (04-design, 05-experiments, 06-conclusion)
│   ├── front_matter/       # Trang bìa, lời cảm ơn, tóm tắt
│   ├── end_matter/         # Phụ lục, tài liệu tham khảo
│   ├── figs/               # Hình ảnh, biểu đồ
│   ├── metrics/            # Số liệu sinh tự động
│   ├── main.tex            # File LaTeX chính
│   ├── references.bib      # Tài liệu tham khảo
│   └── style.tex           # Style definitions
│
├── protocols/              # 📋 Quy trình thực nghiệm
│   ├── Protocol-Reproducible-End-to-End-VNAI-Validation.md
│   └── Protocol-Synthetic-User-Perturbation-Benchmark-Google-Ground-Truth.md
│
├── reports/                # 📊 Báo cáo tổng hợp
│   ├── VNAI-he-thong-thuc-hien-tong-hop.md
│   ├── MAPPING-PROOF-REPORT.md
│   └── VISUAL-MAPPING-DIAGRAM.md
│
├── archive/                # 🗄️ Session reports & old drafts
│   └── (32+ session completion reports, old LaTeX files)
│
└── README.md               # File này
```

---

## 🎯 Mục đích

Thư mục này chứa **Chương 4–6** (thiết kế, thực nghiệm, kết luận) viết dưới dạng báo cáo nghiên cứu; nội dung phải **bám thực nghiệm** và **có thể đối chiếu** với mã nguồn trong repo.

---

## 📘 LaTeX Thesis (mis-DATN-2026/)

### Biên dịch

```powershell
cd "docs/scientific-report/mis-DATN-2026"
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

(XeLaTeX khuyến nghị vì `\usepackage{fontspec}` + tiếng Việt.)

### Tệp chính

| Tệp | Vai trò |
|-----|--------|
| `main.tex` | File tổng, abstract, bibliography |
| `chapters/vnai-chapter-04-design.tex` | Chương 4 — Yêu cầu & Kiến trúc |
| `chapters/vnai-chapter-05-experiments.tex` | Chương 5 — Chỉ số + Audit + Bảng đồng bộ artifact |
| `chapters/vnai-chapter-06-conclusion.tex` | Chương 6 — Kết luận, hạn chế có căn cứ đo được |
| `metrics/vnai-generated-metrics.tex` | **Sinh tự động** — Macro từ `training_log.json` + JSON audit |

---

## 📋 Protocols (protocols/)

Quy trình thực nghiệm chi tiết:

- **Protocol-Reproducible-End-to-End-VNAI-Validation.md**: Quy trình validation end-to-end
- **Protocol-Synthetic-User-Perturbation-Benchmark-Google-Ground-Truth.md**: SUPA-Bench protocol

---

## 📊 Reports (reports/)

Báo cáo tổng hợp hệ thống:

- **VNAI-he-thong-thuc-hien-tong-hop.md**: Báo cáo tổng hợp hiện thực hệ thống (92KB)
- **MAPPING-PROOF-REPORT.md**: Báo cáo chứng minh mapping logic
- **VISUAL-MAPPING-DIAGRAM.md**: Sơ đồ trực quan hóa mapping

---

## 🗄️ Archive (archive/)

Chứa:
- 32+ session completion reports (AUDIT-*, COMPLETION-*, LATEX-*, SESSION-*, etc.)
- Old thesis drafts (MIS_Luan_Van_Tot_Nghiep-*.md)
- Duplicate LaTeX files (vnai-chapter-*.tex cũ)

**Lưu ý:** Files trong archive được giữ lại cho mục đích tham khảo lịch sử, không dùng cho luận văn chính thức.

---

## 🔄 Luồng một lần chạy (repo)

Sau khi cấu hình DB và (tuỳ) HF, dùng orchestrator ở `scripts/flow/` để:

```
regression → audit (JSON) → experiment_runner → production_pipeline pilot → NER smoke → generate_scientific_report_metrics.py
```

→ Cập nhật **`mis-DATN-2026/metrics/vnai-generated-metrics.tex`**

Chi tiết: [`scripts/flow/README.md`](../../scripts/flow/README.md)

---

## ✅ Nguyên tắc minh chứng (bắt buộc)

1. **Số liệu từ DB / audit:** Chỉ ghi sau khi đã chạy script tương ứng; trong LaTeX nêu rõ lệnh (ví dụ `python scripts/diagnostics/audit_acq_admin_bridge.py --write-json ...`) và **thời điểm** hoặc **hash commit** nếu cần trích dẫn trong luận.

2. **Số liệu mô hình (F1, Acc, …):** Đồng bộ từ `training_log.json` / CSV thực nghiệm qua generator — **không** bịa đặt hoặc ước lượng tay trong `.tex` chính.

3. **Tách bạch:** *Mục tiêu ngưỡng* (Gate B P---F1 / P---Acc) khác *kết quả đo được*; audit bridge là **quan sát schema/lineage** trên queue, không thay thế báo cáo huấn luyện NER đầy đủ.

---

## 📚 Tài liệu liên quan

- **Documentation Center**: `docs/INDEX.md`
- **SUPA Benchmark Runbook**: `docs/07-scientific-reports/SUPA-Benchmark-Runbook.md`
- **System Implementation Report**: `docs/07-scientific-reports/VNAI-System-Implementation-Report.md`
- **Training Guide**: `docs/TRAINING-COMMAND-GUIDE.md`

---

**Cập nhật lần cuối:** 2026-05-17  
**Cấu trúc mới:** Tổ chức lại từ 47 files → 4 thư mục rõ ràng
