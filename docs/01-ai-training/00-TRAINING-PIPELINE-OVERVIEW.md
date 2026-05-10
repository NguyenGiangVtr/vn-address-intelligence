# Training pipeline — tổng quan (rút gọn)

**Cập nhật:** 2026-05-10  

**Runbook vận hành bốn giai đoạn:** **[11-OPERATING-PHASES-ABCD.md](11-OPERATING-PHASES-ABCD.md)**  
(A: dữ liệu + train → B: khóa KPI & regression → C: cleanse queue → D: release parser/UI).

## Kiến trúc thành phần (đọc chi tiết trong từng file)

| Thành phần | Tài liệu |
|------------|----------|
| NER / nhãn | `01-NER_Entities.md` |
| PreLabeler (rule) | `02-PreLabeler.md` |
| Siamese PhoBERT | `03-PhoBERT_Siamese.md` |
| Siamese mGTE | `04-mGTE_Siamese.md` |
| LLM | `05-Qwen_LLM.md` |
| Hiệu năng | `06-Performance_Optimization.md` |
| Parser / UI | `07-UI_Parser_Integration.md` |

## Code chính

- Hybrid production: `app/ai/production_pipeline.py`
- Export / PreLabeler: `app/ai/export_for_annotation.py`
- Lineage queue ↔ master v1: `app/domain/acq_mat_lineage.py`

Các file `08`, `09`, `10`, `production-playbook-execution-flow.md`, `training-phase-plan.md`, `ai-training-workflow-summary.md` chỉ còn **redirect** tới doc `11`.
