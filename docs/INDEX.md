# 📚 Documentation Index

Hệ thống tài liệu được tổ chức theo nhóm chức năng để dễ dàng tìm kiếm và quản lý.

---

## 🤖 AI & Training - `01-ai-training/`
Tài liệu về mô hình NER, quy trình huấn luyện, pre-labeling, và Colab

**📊 Tổng hợp Toàn bộ Hệ thống:**
- **[00-TRAINING-PIPELINE-OVERVIEW.md](01-ai-training/00-TRAINING-PIPELINE-OVERVIEW.md)** ⭐ **CHỈ MỤC MỚI** - Toàn bộ quy trình training (5 Phase, IPO chi tiết, thứ tự, KPI, kiểm chứng)

**Tài liệu chi tiết từng Model (NEW):**
- **[01-NER_Entities.md](01-ai-training/01-NER_Entities.md)** - PhoBERT NER: Input → Process → Output, Database, UI/UX, Metrics, Validation
- **[02-PreLabeler.md](01-ai-training/02-PreLabeler.md)** - Hybrid Auto-Annotation: Macro + Micro labeling, Label Studio format
- **[03-PhoBERT_Siamese.md](01-ai-training/03-PhoBERT_Siamese.md)** - Dense Retriever (Vietnamese): Corpus encoding, retrieval, performance benchmark
- **[04-mGTE_Siamese.md](01-ai-training/04-mGTE_Siamese.md)** - Multilingual Siamese (Baseline): Zero-shot, latency comparison vs PhoBERT
- **[05-Qwen_LLM.md](01-ai-training/05-Qwen_LLM.md)** - LLM Normalization: Prompt engineering, JSON parsing, confidence scoring

**Tài liệu cũ (reference):**
- [ai-training-workflow-summary.md](01-ai-training/ai-training-workflow-summary.md) - Legacy workflow (deprecated - dùng 00-TRAINING-PIPELINE-OVERVIEW thay thế)
- [NER-implement-planning.md](01-ai-training/NER-implement-planning.md) - Planning doc
- [training-phase-plan.md](01-ai-training/training-phase-plan.md) - Phase breakdown
- [pre-labeler-planning.md](01-ai-training/pre-labeler-planning.md) - Pre-labeling strategy
- [colab_guide.md](01-ai-training/colab_guide.md) - Google Colab setup

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
- **[address-parser-plan.md](03-ui-frontend/address-parser-plan.md)** - Kế hoạch chi tiết Address Parser

---

## 🗺️ Geospatial & GIS - `04-geospatial/`
Bản đồ, OSM, ranh giới hành chính, visualization

- **[boundary_visualization_integration.md](04-geospatial/boundary_visualization_integration.md)** - Tích hợp visualization ranh giới
- **[osm-pull-data-plan.md](04-geospatial/osm-pull-data-plan.md)** - Kế hoạch kéo dữ liệu OpenStreetMap

---

## 🚀 Deployment & Operations - `05-deployment/`
Triển khai, production, monitoring

- **[deploy-guide.md](05-deployment/deploy-guide.md)** - Hướng dẫn triển khai hệ thống

---

## 📋 Planning & Reference - `06-planning-reference/`
Tài liệu hoạch định, tham chiếu nhanh, phân tích

- **[quick_reference.md](06-planning-reference/quick_reference.md)** - Tham chiếu nhanh lệnh, API, workflow
- **[feature-status-analysis.md](06-planning-reference/feature-status-analysis.md)** - Phân tích trạng thái tính năng
- **[suggest-plan.md](06-planning-reference/suggest-plan.md)** - Đề xuất kế hoạch phát triển
- **[restructure_plan.md](06-planning-reference/restructure_plan.md)** - Kế hoạch tái cấu trúc codebase
- **[project_memory.md](06-planning-reference/project_memory.md)** - Ghi chú dự án, lộ trình

---

## 📦 Thư mục khác
- **n8n/** - Workflow N8N automation
- **private/** - Tài liệu nội bộ, báo cáo, nghiên cứu

---

## 💡 Mẹo sử dụng
- Khi bắt đầu dự án mới, xem `06-planning-reference/quick_reference.md`
- Để hiểu kiến trúc DB, xem `02-database/database.md`
- Để setup huấn luyện mô hình, bắt đầu từ `01-ai-training/ai-training-workflow-summary.md`
- Để phát triển UI, tham khảo `03-ui-frontend/address-parser-plan.md`

