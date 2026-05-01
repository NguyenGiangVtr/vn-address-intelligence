# INSTRUCTIONS.md — VN Address Intelligence

## Đề tài Nghiên cứu
**Xây dựng khung Giải pháp Làm giàu và Chuẩn hóa Dữ liệu Địa chỉ Việt Nam sử dụng Tiếp cận Đa nguồn và Thuật toán Hình học Không gian trong bối cảnh Sắp xếp Đơn vị Hành chính toàn quốc 2025**

- Học viên: Nguyễn Vũ Trọng Giang – MSHV: 2470279
- Chuyên ngành: Hệ thống Thông tin Quản lý (MIS)
- GVHD: PGS. TS. Trần Minh Quang

---

## 1. Nguyên tắc Phát triển (Karpathy Principles)

### 1.1. Think Before Coding
- **KHÔNG giả định** — Nếu không chắc, hỏi lại thay vì đoán.
- Trình bày các phương án khác nhau khi có sự mơ hồ.
- Phản đối nếu có cách đơn giản hơn. Giải thích lý do.
- Dừng lại khi bối rối — nêu rõ điều chưa hiểu.

### 1.2. Simplicity First
- Code tối thiểu giải quyết đúng bài toán. Không đoán trước tương lai.
- Không thêm feature ngoài yêu cầu. Không tạo abstraction cho code dùng 1 lần.
- Không xử lý lỗi cho các trường hợp bất khả thi.
- Nếu 200 dòng có thể viết lại thành 50 dòng — viết lại.

### 1.3. Surgical Changes
- Chỉ sửa đúng phần được yêu cầu. Không "cải tiến" code lân cận.
- Giữ nguyên style hiện tại, kể cả khi muốn làm khác.
- Nếu thấy dead code không liên quan — chỉ thông báo, không xóa.
- Mỗi dòng thay đổi phải trace trực tiếp đến yêu cầu của user.

### 1.4. Goal-Driven Execution
- Xác định tiêu chí thành công trước khi code.
- Với multi-step task, liệt kê plan kèm verification:
  ```
  1. [Bước] → verify: [kiểm tra gì]
  2. [Bước] → verify: [kiểm tra gì]
  ```
- Lặp cho đến khi đạt tiêu chí. Không "xong rồi" nếu chưa verify.

---

## 2. Bối cảnh Nghiên cứu

### 2.1. Bài toán
Dữ liệu địa chỉ từ CRM doanh nghiệp thường:
- **Over-information**: Người dùng copy-paste lặp lại nhiều cấp hành chính
- **Under-information**: Chỉ chọn dropdown Tỉnh/Huyện/Xã nhưng bỏ trống số nhà

Hệ thống giải quyết bằng pipeline: SQL Preprocessing → NER (PhoBERT) → Siamese Network → LLM Validation.

### 2.2. Kế thừa Khoa học
- **Siamese Network** (Cao Hai-Nam, 2021): Kiến trúc Bi-Encoder cho address matching
- **BIO tagging** (Đặng Đức Tùng, 2019): Gán nhãn thực thể địa chỉ
- Mở rộng quy mô dữ liệu gấp **50 lần** so với nghiên cứu gốc

### 2.3. Tiêu chí Đánh giá (Góc nhìn MIS)
| Chỉ số | Kỳ vọng |
|---|---|
| F1-Score NER | ≥ 82% |
| Throughput | ≥ 20 địa chỉ/giây |
| Chi phí / 1M địa chỉ | < $100 (vs $5.000 Google API) |
| Tỷ lệ khớp Google Maps | ≥ 75% |

---

## 3. Kiến trúc Hệ thống

### 3.1. Database (PostgreSQL)
```
Schema mat: Master Data hành chính (Province, District, Ward, WardMapping)
Schema osm: OpenStreetMap (Streets, Buildings, POIs, RawEntities)
Schema ath: AI Training Hub (TrainingDatasets)
Schema prq: Processing Queue (AddressCleansingQueue — bảng chính)
```

**Bảng chính**: `prq.address_cleansing_queue` (~505K rows)
- `raw_address`: Địa chỉ thô gốc (INPUT)
- `street_address`: Lõi địa chỉ đã bóc tách bởi SQL
- `address_standardized`: Kết quả cuối cùng sau AI (OUTPUT)

### 3.2. AI Models (app/ai/)
| Model | File | Vai trò |
|---|---|---|
| PhoBERT NER | `models/ner_model.py` | Bóc tách thực thể địa chỉ (10 labels) |
| PhoBERT Siamese | `models/phobert_model.py` | Address matching (Bi-Encoder) |
| mGTE Siamese | `models/siamese_mgte.py` | Multilingual baseline |
| LLM Qwen3 | `models/llm_model.py` | Final normalization |

### 3.3. NER Labels (Source of Truth: `app/ai/constants.py`)
Mọi thay đổi label CHỈ sửa tại `constants.py`. Các file khác auto đồng bộ.

| Code | Tên | Hotkey |
|---|---|---|
| PCD | Plus Code | 0 |
| BLD | Tòa nhà/Chung cư | 1 |
| POI | Địa danh/Mốc/Cửa hàng | 2 |
| ALY | Hẻm/Ngõ | 3 |
| NUM | Số nhà / Lô / P. | 4 |
| STR | Tên đường | 5 |
| NHB | Khu phố/Thôn/Ấp/Làng/Xóm | 6 |
| WDS | Phường/Xã | 7 |
| DST | Quận/Huyện | 8 |
| PRO | Tỉnh/Thành phố | 9 |

---

## 4. Cấu trúc Dự án

```
vn-address-intelligence/
├── app/
│   ├── main.py                    # CLI entry (check-db, serve-ui)
│   ├── core/
│   │   ├── config.py              # App config (từ .env)
│   │   └── database.py            # SQLAlchemy models
│   ├── ai/
│   │   ├── constants.py           # ★ NER Labels — Source of Truth
│   │   ├── config.yaml            # AI/Experiment config (dùng ${ENV_VAR})
│   │   ├── train_ner.py           # Fine-tune PhoBERT NER
│   │   ├── export_for_annotation.py  # Hybrid PreLabeler → Label Studio
│   │   ├── experiment_runner.py   # So sánh 3 mô hình
│   │   ├── production_pipeline.py # Hybrid pipeline: NER + Siamese + LLM
│   │   ├── metrics.py             # Exact Match, Fuzzy, Component Accuracy
│   │   ├── report_generator.py    # HTML + CSV reports
│   │   ├── db_connector.py        # PostgreSQL connector
│   │   ├── models/
│   │   │   ├── ner_model.py       # AddressNER (PhoBERT Token Classification)
│   │   │   ├── phobert_model.py   # PhoBERTSiamese (Bi-Encoder)
│   │   │   ├── siamese_mgte.py    # SiameseMGTE (multilingual baseline)
│   │   │   └── llm_model.py       # LLMQwen3 (generation)
│   │   └── utils/
│   │       └── config_loader.py   # YAML + .env resolver
│   └── services/                  # Business logic layer
├── ui/                            # SaaS Frontend (Linear Design System)
├── data/                          # Exported datasets + Label Studio files
├── docs/                          # Research documentation
├── scripts/                       # Utility scripts
├── models/                        # Saved AI models (gitignored)
├── reports/                       # Experiment reports
├── .env                           # Secrets (gitignored)
├── .env.example                   # Template
├── start.py                       # Main entry point
└── requirements.txt
```

---

## 5. Quy tắc Bảo mật

### TUYỆT ĐỐI KHÔNG:
- Hardcode password, IP, API key trong source code
- Commit file `.env` vào git
- Log sensitive data (passwords, tokens)
- Expose database credentials trong output/reports

### PHẢI:
- Sử dụng `.env` + `os.getenv()` cho mọi credentials
- Sử dụng `load_config_with_env()` (từ `utils/config_loader.py`) cho YAML config
- Placeholder `${DB_HOST}`, `${DB_PASS}` trong config.yaml
- Kiểm tra `.gitignore` bao gồm: `.env`, `logs/`, `evidence/`, `models/`, `data/*.json`

---

## 6. Quy tắc Code

### 6.1. Python
- Python 3.11+
- Encoding: UTF-8 (Windows terminal dùng cp1252 — tránh emoji trong click.echo)
- Logging: `logging` module, format `%(asctime)s [%(levelname)s] %(message)s`
- Import path: Scripts trong `app/ai/` dùng `sys.path.insert(0, str(Path(__file__).parent))`

### 6.2. Database
- Cột địa chỉ thô: `raw_address`
- Bảng chính: `prq.address_cleansing_queue`
- Luôn dùng parameterized queries, không string interpolation cho WHERE clause
- JOIN master data qua: `mat.ward`, `mat.district`, `mat.province`

### 6.3. AI / ML
- Label changes: CHỈ sửa `app/ai/constants.py` — tất cả scripts auto đồng bộ
- Training data format: Label Studio JSON → BIO tokens (xem `train_ner.py`)
- PhoBERT tokenizer: Slow tokenizer (không hỗ trợ `return_offset_mapping`) — dùng word-level tokenization rồi expand
- Model output: Lưu tại `models/phobert-ner-vn/`
- Evaluation: `seqeval` library cho NER, `metrics.py` cho address normalization

### 6.4. Filename Conventions
- Export files: `ner_samples_{yyyyMMdd_HHmmss}_{limit}_prelabeled.json`
- Config files: Tương tự nhưng suffix `_config.xml`
- Reports: `reports/experiment_report.html`, `reports/experiment_results.csv`

---

## 7. UI / Frontend (SaaS Tool)

### 7.1. Design System
- Theme: **Linear Design System** — `npx getdesign@latest add linear.app`
- Dark mode by default, glassmorphism, micro-animations
- Typography: Inter / Roboto from Google Fonts
- Responsive layout, mobile-friendly

### 7.2. SaaS Features (Tương lai)
Mỗi tính năng AI đều phải có UI tương ứng:

| Feature | Mô tả | Endpoint |
|---|---|---|
| **Address Parser** | Paste địa chỉ → NER bóc tách realtime | `/api/v1/parse` |
| **Batch Processor** | Upload CSV → xử lý hàng loạt | `/api/v1/batch` |
| **Dashboard** | Thống kê database, tiến độ xử lý | `/dashboard` |
| **Model Comparison** | So sánh kết quả 3 mô hình | `/experiments` |
| **Ward Mapper** | Tra cứu sáp nhập hành chính 2025 | `/ward-mapping` |
| **Data Explorer** | Duyệt + tìm kiếm dữ liệu trong queue | `/explorer` |
| **Label Studio Export** | Xuất dữ liệu cho gán nhãn | `/export` |

### 7.3. Nguyên tắc UI
- Mỗi tool AI tạo ra PHẢI có giao diện sử dụng trên UI
- Không tạo tool chỉ chạy bằng CLI mà không có UI tương ứng
- Ưu tiên visual feedback: progress bars, real-time logs, interactive tables
- Error messages phải rõ ràng, actionable

---

## 8. Quy trình Phát triển

### 8.1. Khi thêm Label mới
1. Sửa `app/ai/constants.py` (NER_LABELS)
2. Kiểm tra: `train_ner.py`, `export_for_annotation.py`, `ner_model.py` auto đồng bộ
3. Chạy export lại: `python app/ai/export_for_annotation.py --limit 100`

### 8.2. Khi thay đổi Database schema
1. Cập nhật `app/core/database.py` (SQLAlchemy models)
2. Grep toàn bộ codebase: `grep -r "old_column_name" app/ docs/ scripts/`
3. Cập nhật SQL queries trong: `export_for_annotation.py`, `production_pipeline.py`, `experiment_runner.py`
4. Cập nhật docs: `database.md`, `project_memory.md`

### 8.3. Khi huấn luyện model
```bash
# Validate BIO conversion trước
python app/ai/train_ner.py --data data/labeled_export.json --validate-only

# Train
python app/ai/train_ner.py --data data/labeled_export.json --epochs 15 --batch-size 16

# Chạy experiment
python app/ai/experiment_runner.py --config app/ai/config.yaml
```

---

## 9. Lưu ý Quan trọng cho Agent

- **Luôn bám sát đề tài nghiên cứu**: Mọi feature phải phục vụ mục tiêu "Làm giàu và Chuẩn hóa Dữ liệu Địa chỉ Việt Nam". Không đi lạc sang bài toán khác.
- **Ưu tiên giá trị MIS**: Tối ưu chi phí, throughput, khả năng tự động hóa. Không chạy theo accuracy thuần túy.
- **Deadline cứng**: 25/05/2026 nộp quyển. Mọi quyết định kỹ thuật phải cân nhắc thời gian.
- **Dữ liệu thực tế**: 505.094 địa chỉ CRM thực. Không dùng dummy data cho evaluation.
- **Bối cảnh hành chính 2025**: Hệ thống phải xử lý được cả địa chỉ cũ (trước sáp nhập) và mới. Dùng `mat.ward_mapping` để chuyển đổi.
