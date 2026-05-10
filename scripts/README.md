# Scripts & deploy

## Deploy nhanh (PowerShell)

```powershell
# Deploy lên VPS (wrapper → scripts/release/deploy.ps1)
.\scripts\deploy.ps1

# Chỉ restart service
.\scripts\deploy.ps1 -RestartOnly
```

## Build publish (đồng bộ CI)

```powershell
# Canonical: CI-parity bundle
.\scripts\release\publish.ps1

# Wrapper từ gốc repo
.\scripts\publish.ps1
```

Chi tiết publish: xem comment đầu file `scripts/release/publish.ps1` và [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml).

---

## Mục lục thư mục `scripts/`

| Thư mục | Mục đích |
|---------|-----------|
| `ops/` | Vận hành: embeddings, vector index, corpus, optimize parser — [README](ops/README.md). File tương ứng ở **gốc repo** là shim tương thích. |
| `scratch/` | Thử một lần, debug DB/API — [README](scratch/README.md). |
| `deployment/` | VPS: setup, `deploy.sh`, service template. |
| `release/` | `publish.ps1`, `deploy.ps1` (bundle + upload). |
| `migration/` | Chuyển schema/dữ liệu giữa các phiên bản bảng. |
| `sql/` | File `.sql` + tiện ích áp dụng (vd. `apply_sql_file.py`). |
| `diagnostics/` | Kiểm tra queue, pgvector, NaN, pilot vs ground truth, … |
| `enrichment/` | Làm giàu / sửa batch ngoài luồng API. |
| `labeling/` | PreLabeler: `prelabeler_labeling_cases.json`, regression, refresh. |
| `data/` | Tải dataset ngoài, nạp vào corpus/DB. |
| `reporting/` | Xuất evidence / báo cáo. |
| `test/` | Regression trong repo (vd. `test_prelabeler_regression.py`). |

**File rời ở `scripts/`** (không vào thư mục con): thường là script cũ hoặc entry ngắn — khi sửa lớn nên **gom vào đúng thư mục** phía trên.

---

## Quy ước script mới

1. Đặt vào **một** thư mục con theo bảng; không thêm Python mới ở **root repo** nếu tránh được.
2. Shebang / `python` có thể chạy từ root: `python scripts/diagnostics/check_queue_columns.py`.
3. Phụ thuộc: dùng cùng venv với app; AI labeling cần `requirements-prod.txt` hoặc `requirements.txt` theo rule trong workspace.

---

## Bảo mật (deploy / .env)

- `.env` gitignored; publish local có thể copy `.env` (xem `publish.ps1`).
- Trên VPS quyền file `.env` hạn chế (owner read).

```powershell
Test-Path .env
.\scripts\publish.ps1 -SkipTests
```

---

## Gợi ý xử lý sự cố SSH / API

```powershell
ssh user@HOST 'echo OK'
ssh user@HOST 'sudo systemctl status YOUR_SERVICE'
```

---

**Cấu trúc tổng thể repo**: [`docs/00-ENGINEERING/SOURCE-LAYOUT.md`](../docs/00-ENGINEERING/SOURCE-LAYOUT.md).
