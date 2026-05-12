# Cấu trúc mã nguồn (chuẩn hóa)

Tài liệu **chân** để tra cứu: code nằm đâu, thêm tính năng mới đặt ở đâu, script one-off vs thư viện dùng lại.

---

## 1. Tổng quan thư mục gốc

| Thư mục / file | Vai trò |
|----------------|---------|
| `src/app/` | **Gói ứng dụng Python** (src layout): API, DB, nghiệp vụ, AI — *import được* (`from app...`; cần `pip install -e .` hoặc `PYTHONPATH=src`). |
| `_bootstrap_import_paths.py` | Một số entry script gọi trước `import app` khi chạy file `.py` trực tiếp. |
| `ui/` | Giao diện tĩnh: `index.html`, `app.js`, `pages/*.html`, `style.css`. |
| `docs/` | Markdown: kiến trúc, playbook, đặc tả (`docs/INDEX.md` là mục lục). |
| `scripts/` | Script vận hành/migration/diagnostics — *chạy bằng đường dẫn*, không import như thư viện chính. |
| `data/` | Seed, export, file dữ liệu cục bộ (thường gitignore một phần). |
| `models/` | Artefact huấn luyện / checkpoint (không commit file nặng; giữ cấu trúc thư mục). |
| `.github/workflows/` | CI/CD (deploy tarball, bảo mật). |
| `requirements.txt` / `requirements-prod.txt` | Phụ thuộc dev vs VPS CPU. |
| `start.py` | Wrapper khởi động API nhanh (tham chiếu trong deploy). |
| `pyproject.toml` | Metadata package; setuptools tìm package trong `src/` (`where = ["src"]`). |
| `optimize_parser_performance.py` (gốc) | **Một shim đặc biệt**: `from optimize_parser_performance import …` (PEP 562) + CLI; implementation trong `scripts/ops/optimize_parser_performance.py`. |

Script vận hành corpus/embeddings/vector — **canonical** tại [`scripts/ops/`](../../scripts/ops/README.md). Các lệnh ngắn tương đương `python compute_embeddings.py` (đã bỏ ở gốc) dùng **`python scripts/shims/<tên>.py`** hoặc **`python scripts/ops/<tên>.py`** trực tiếp.

---

## 2. `src/app/` — ranh giới layer

```
src/app/
├── main.py              # CLI Click: init_db, seed, fetch_osm, …
├── paths.py             # Gốc repo (neo `pyproject.toml`), đường dẫn config AI, docs, v.v.
├── api/                 # FastAPI: server.py, deps.py (auth/DB session), state.py + job_runners.py (job nền), routers/, boundary, spatial, schemas, repo_docs
├── core/                # config, database (SQLAlchemy), cache
├── services/            # Nghiệp vụ: OSM, NSO, enrichment, ground truth, auth, crawlers, …
├── ai/                  # Mô hình & pipeline: models/, export_for_annotation (PreLabeler), train_*, experiment_runner, …
├── tools/               # Công cụ gắn domain (vd. boundary_visualization)
└── geometry/            # Xử lý hình học (phục vụ ranh giới / inject)
```

**Quy ước**

- **API chỉ** điều phối: đọc request → gọi service hoặc module `app.ai` → trả response.
- Logic tái sử dụng dài hạn → `app.services` hoặc `app.ai` (tùy domain).
- File chỉ phục vụ một route có thể sát `app.api` nhưng tránh làm phồng `server.py` (tách module con đã có mẫu: `boundary.py`, `repo_docs.py`; thêm router trong `api/routers/` khi nhóm endpoint lớn).

---

## 3. `scripts/` — nhóm chức năng

| Thư mục | Nội dung típ |
|---------|----------------|
| `ops/` | Vận hành DB/corpus: embeddings, vector index, tối ưu parser, corpus quick setup, script tạm/debug. Xem `scripts/ops/README.md`. |
| `scratch/` | Thử nghiệm một lần (không dùng trong prod); có `_repo_bootstrap` giống `ops/`. |
| `deployment/` | `deploy.sh`, `vnai-vps-setup.sh`, cấu hình service. |
| `release/` | `publish.ps1` (bundle thư mục publish — đồng bộ CI). |
| `migration/` | Đổi schema, migrate dữ liệu giữa bảng/schema. |
| `sql/` | SQL thuần + helper `apply_sql_file.py`. |
| `diagnostics/` | Kiểm tra DB, queue, vector, sanity (chạy khi debug). |
| `enrichment/` | Pipeline làm giàu / sửa batch ngoài API. |
| `labeling/` | PreLabeler: case JSON, `run_prelabeler_labeling_cases.py`, refresh. |
| `data/` | Tải / nạp dataset ngoài (HF → corpus, …). |
| `reporting/` | Xuất evidence, báo cáo. |
| `test/` | Kiểm thử regression gắn repo (PreLabeler, v.v.). |

Script **mới**: chọn đúng thư mục; tiện ích vận hành tổng quát → `scripts/ops/` và cập nhật `scripts/ops/README.md`.

**`optimize_parser_performance`**: vẫn hỗ trợ `python -c "from optimize_parser_performance import OptimizedParserPipeline"` nhờ shim PEP 562 tại gốc.

---

## 4. `ui/` — trang và tài nguyên

- `index.html`: shell + sidebar (`data-page` → `ui/pages/<id>.html`).
- `app.js`: điều phớt trang, gọi API; không nhét logic nghiệp vụ nặng.
- `pages/*.html`: từng màn hình; asset version qua query `?v=` (CI/publish).
- `pages/generated/`: artefact HTML tạo động (vd. bản đồ ranh giới), URL `/pages/generated/...`.

---

## 5. Tài liệu liên quan

- Mục lục docs: [`docs/INDEX.md`](../INDEX.md)
- Bối cảnh nhanh backend: [`CODEBASE_CONTEXT.md`](../../CODEBASE_CONTEXT.md)
- Mục lục script & deploy: [`scripts/README.md`](../../scripts/README.md)
- Kế hoạch refactor cũ (tham chiếu): [`06-planning-reference/restructure_plan.md`](../06-planning-reference/restructure_plan.md)

---

## 6. Checklist khi thêm tính năng

1. API mới → `src/app/api/` (module riêng nếu đủ lớn) + test tay route.
2. Quy tắc nghiệp vụ → `src/app/services/` (hoặc `src/app/ai/` nếu chỉ ML).
3. Script một lần / vận hành → `scripts/<nhóm>/`.
4. Tài liệu hướng dẫn → `docs/` + một dòng trong `INDEX.md` nếu là tài liệu chính.
