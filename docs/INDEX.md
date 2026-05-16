# 📚 Documentation Index

Hệ thống tài liệu được tổ chức theo nhóm chức năng để dễ dàng tìm kiếm và quản lý.

**Nguồn chân:** toàn bộ nội dung đọc trên Web UI là các tệp **`.md` trong `docs/`** (không có bản HTML tĩnh trùng lặp). Trong SaaS sau khi đăng nhập: menu **AI & Benchmark → Trung tâm tài liệu** (`#/documentation`). Máy chủ phục vụ file qua `GET /api/repo-docs/list` và `GET /api/repo-docs/raw/{đường_dẫn}.md`; không cần bước convert sang HTML khi chỉnh sửa trong Git.

---

## 🧱 Cấu trúc mã & kỹ thuật - `00-ENGINEERING/`

- **[SOURCE-LAYOUT.md](00-ENGINEERING/SOURCE-LAYOUT.md)** — Cây thư mục chuẩn, ranh giới `app/` vs `scripts/`, checklist khi thêm tính năng  
- **Script & deploy:** [`scripts/README.md`](../scripts/README.md) · vận hành corpus/embeddings: [`scripts/ops/README.md`](../scripts/ops/README.md)

---

## 🤖 AI & Training - `01-ai-training/`
Tài liệu về mô hình NER, quy trình huấn luyện, pre-labeling, và Colab

**📊 Runbook vận hành (nguồn chân duy nhất):**
- **[11-OPERATING-PHASES-ABCD.md](01-ai-training/11-OPERATING-PHASES-ABCD.md)** — **A→B→C→D:** train & dữ liệu → khóa KPI → cleanse queue → release parser/UI  
- **[00-TRAINING-PIPELINE-OVERVIEW.md](01-ai-training/00-TRAINING-PIPELINE-OVERVIEW.md)** — Tổng quan ngắn + link sang model docs

**Tài liệu chi tiết từng Model:**
- **[01-NER_Entities.md](01-ai-training/01-NER_Entities.md)** - PhoBERT NER: Input → Process → Output, Database, UI/UX, Metrics, Validation
- **[02-PreLabeler.md](01-ai-training/02-PreLabeler.md)** - Hybrid Auto-Annotation: Macro + Micro labeling, Label Studio format
- **[03-PhoBERT_Siamese.md](01-ai-training/03-PhoBERT_Siamese.md)** - Dense Retriever (Vietnamese): Corpus encoding, retrieval, performance benchmark
- **[04-mGTE_Siamese.md](01-ai-training/04-mGTE_Siamese.md)** - Multilingual Siamese (Baseline): Zero-shot, latency comparison vs PhoBERT
- **[05-Qwen_LLM.md](01-ai-training/05-Qwen_LLM.md)** - LLM Normalization: Prompt engineering, JSON parsing, confidence scoring
- **[06-Performance_Optimization.md](01-ai-training/06-Performance_Optimization.md)** - Performance Optimization: Caching, parallel processing, embedding pre-computation

**Khác:**
- [colab_guide.md](01-ai-training/colab_guide.md) — Google Colab (tuỳ chọn)

---

## 🗄️ Database & SQL - `02-database/`
Schema, migrations, và câu lệnh SQL

- **[database.md](02-database/database.md)** - Thiết kế schema, data model
- **[update_address_smart.sql](02-database/update_address_smart.sql)** - SQL scripts cập nhật dữ liệu

---

## 🎨 UI/UX & Frontend - `03-ui-frontend/`
Giao diện người dùng, layout, flow, và thiết kế

- **[ui_implementation_plan.md](03-ui-frontend/ui_implementation_plan.md)** - Kế hoạch triển khai UI
- **[new-ui-ides.md](03-ui-frontend/new-ui-ides.md)** - Ý tưởng UI mới
- **[address-parser-flow.md](03-ui-frontend/address-parser-flow.md)** - Luồng xử lý Address Parser

---

## 🗺️ Geospatial & GIS - `04-geospatial/`
Bản đồ, OSM, ranh giới hành chính, visualization

- **[boundary_visualization_integration.md](04-geospatial/boundary_visualization_integration.md)** - Tích hợp visualization ranh giới
- **[osm-pull-data-plan.md](04-geospatial/osm-pull-data-plan.md)** - Kế hoạch kéo dữ liệu OpenStreetMap

---

## 🚀 Deployment & Operations - `05-deployment/`
Triển khai, production, monitoring

- **[deploy-guide.md](05-deployment/deploy-guide.md)** - Hướng dẫn triển khai hệ thống
- **[PUBLISH_GUIDE.md](05-deployment/PUBLISH_GUIDE.md)** - Hướng dẫn publish và release

---

## 📋 Planning & Reference - `06-planning-reference/`
Tài liệu hoạch định, tham chiếu nhanh, phân tích

- **[quick_reference.md](06-planning-reference/quick_reference.md)** - Tham chiếu nhanh lệnh, API, workflow
- **[feature-status-analysis.md](06-planning-reference/feature-status-analysis.md)** - Phân tích trạng thái tính năng
- **[suggest-plan.md](06-planning-reference/suggest-plan.md)** - Đề xuất kế hoạch phát triển
- **[restructure_plan.md](06-planning-reference/restructure_plan.md)** - Kế hoạch tái cấu trúc codebase
- **[project_memory.md](06-planning-reference/project_memory.md)** - Ghi chú dự án, lộ trình
- **[TODO.md](06-planning-reference/TODO.md)** - Danh sách công việc cần làm
- **[RUN_ORDER.md](06-planning-reference/RUN_ORDER.md)** - Thứ tự chạy các scripts và commands

---

## 📊 Scientific Reports - `07-scientific-reports/`
Báo cáo khoa học, runbook thực nghiệm, kết quả đánh giá

- **[VNAI-System-Implementation-Report.md](07-scientific-reports/VNAI-System-Implementation-Report.md)** - Báo cáo tổng hợp hiện thực hệ thống trí tuệ địa chỉ Việt Nam (630 dòng) - Kiến trúc, pipeline AI, thực nghiệm SUPA-Bench, kết quả định lượng
- **[SUPA-Benchmark-Runbook.md](07-scientific-reports/SUPA-Benchmark-Runbook.md)** - Runbook SUPA-Bench: extract cohort, apply noise, import predictions, eval metrics (389 dòng) - Hướng dẫn chi tiết từng bước thực nghiệm

---

## 📦 Thư mục khác
- **n8n/** - Workflow N8N automation
- **typesense/** - Typesense schema definitions
- **private/** - Tài liệu nội bộ, archive (không hiển thị trong Documentation Center)

---

## 💡 Mẹo sử dụng
- Khi bắt đầu dự án mới, xem `06-planning-reference/quick_reference.md`
- Để hiểu kiến trúc DB, xem `02-database/database.md`
- Để setup huấn luyện + cleanse queue: **`01-ai-training/11-OPERATING-PHASES-ABCD.md`**; lineage queue ↔ master: `.cursor/rules/address-queue-mat-lineage.mdc` và `app/domain/acq_mat_lineage.py`
- Để phát triển UI, tham khảo `03-ui-frontend/ui_implementation_plan.md`
- Để chạy thực nghiệm SUPA-Bench: **`07-scientific-reports/SUPA-Benchmark-Runbook.md`**
- Để hiểu toàn bộ hệ thống: **`07-scientific-reports/VNAI-System-Implementation-Report.md`**

