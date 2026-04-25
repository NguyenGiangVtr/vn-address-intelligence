# 🇻🇳 VN Address Intelligence (VNAI) v2.0

> **Hệ thống AI chuẩn hóa và làm giàu dữ liệu địa chỉ Việt Nam phi cấu trúc**, tuân thủ các biến động hành chính 2025 (Admin V2). Kết hợp PhoBERT, Siamese Network và Web Dashboard quản trị thời gian thực.

---

## 📋 Tổng quan
VN Address Intelligence không chỉ là một mô hình NLP, mà là một **Hệ sinh thái Dữ liệu địa chỉ** toàn diện, giải quyết các thách thức:
- **Biến động hành chính 2025**: Tự động ánh xạ xã/phường sáp nhập theo các Nghị quyết mới nhất của Chính phủ (Admin V2).
- **Quy mô dữ liệu khổng lồ**: Hệ thống quản lý hơn **1.35 triệu** bản ghi thực địa từ OpenStreetMap (OSM) với mục tiêu đạt **5 triệu** bản ghi.
- **Chuẩn hóa đa mô hình**: So sánh hiệu năng giữa PhoBERT, mGTE và LLM (Qwen/Gemini) để tìm ra kết quả chính xác nhất.
- **Giá trị MIS**: Tối ưu hóa 98% chi phí so với các giải pháp Cloud API (Google/Bing) và nâng cao hiệu quả vận hành doanh nghiệp.

---

## 🏗️ Kiến trúc Hệ thống

### 1. Data Intelligence Core
- **Master Data (mat)**: Quản lý 63 tỉnh thành, 767 quận/huyện và 15k+ xã/phường. Tích hợp SCD Type 2 để theo dõi lịch sử sáp nhập.
- **OSM Data Hub (osm)**: Pipeline thu thập dữ liệu thực địa (Streets, Buildings, POIs) tự động với cơ chế xoay vòng Overpass API server.
- **AI Training Hub (ath)**: Tự động sinh tập dữ liệu huấn luyện (Synthetic Data) với gán nhãn BIO tự động.

### 2. Pipeline Chuẩn hóa (Standardization)
Hệ thống sử dụng kiến trúc **Ensemble 4 Tầng** tối ưu:
- **Tầng 1 (ColBERT)**: Tìm kiếm nhanh ứng viên tiềm năng (~45ms).
- **Tầng 2 (mGTE)**: Tính toán tương đồng ngữ nghĩa (Semantic Similarity).
- **Tầng 3 (Cross-Encoder)**: Tái xếp hạng chính xác cao.
- **Tầng 4 (LLM Fallback)**: Xử lý các địa chỉ cực khó hoặc bị nhiễu nặng.

---

## 🖥️ Giao diện Quản trị (Web Dashboard)
Hệ thống cung cấp Dashboard hiện đại (Dark Mode, Glassmorphism) để theo dõi và quản lý dữ liệu:
- **Overview**: Biểu đồ tăng trưởng dữ liệu và sức khỏe hệ thống.
- **Admin Explorer**: Tra cứu các Nghị quyết sáp nhập và tình trạng làm giàu dữ liệu từng tỉnh.
- **OSM Monitoring**: Giám sát tiến trình crawl dữ liệu bản đồ.
- **AI Hub**: Xem trước các mẫu dữ liệu huấn luyện và trạng thái mô hình.

**Khởi chạy UI:**
```bash
python start.py serve-ui
# Hoặc trực tiếp:
python -m app.api.server
# Truy cập: http://localhost:8080
```

---

## 🚀 Hướng dẫn Sử dụng (CLI)

Dự án cung cấp bộ công cụ CLI mạnh mẽ qua `main.py`:

| Lệnh | Mô tả |
|---|---|
| `python start.py check-db` | Kiểm tra thống kê dữ liệu & tốc độ tăng trưởng |
| `python start.py fetch-osm --target 5000000` | Khởi chạy tiến trình crawl OSM (Mục tiêu 5M) |
| `python start.py enrich-v2` | Làm giàu dữ liệu GSO & Cập nhật Admin V2 |
| `python scripts/export_evidence.py` | Trích xuất file minh chứng (CSV) gửi báo cáo |

---

## 📁 Cấu trúc Dự án
```text
vn-address-intelligence/
├── app/                    # Mã nguồn chính (FastAPI, CLI, Services, AI)
│   ├── api/                # API Endpoints & Server
│   ├── core/               # Cấu hình & Kết nối Database
│   ├── services/           # Logic nghiệp vụ (Crawlers, OSM Fetchers)
│   ├── ai/                 # Nghiên cứu & Huấn luyện mô hình NER
│   └── main.py             # Entry point cho CLI
├── ui/                     # Giao diện người dùng (Dashboard)
├── scripts/                # Các kịch bản bảo trì & trích xuất
├── data/                   # Dữ liệu cục bộ (Seed CSV, JSON)
├── docs/                   # Tài liệu hướng dẫn & Báo cáo
├── logs/                   # Nhật ký hệ thống
├── start.py                # Wrapper script để chạy CLI/Server
└── requirements.txt        # Danh sách thư viện phụ thuộc
```

---

## 📊 Minh chứng & Kết quả (Tính đến 25/04/2026)

Hệ thống đã đạt được các cột mốc quan trọng:
- **1.35M+** bản ghi thực địa được chuẩn hóa.
- **100%** tỉnh thành được làm giàu thông tin pháp lý 2025.
- **25k+** mẫu dữ liệu huấn luyện gán nhãn BIO sẵn sàng.
- **Tốc độ tăng trưởng**: ~100k bản ghi mới / 3 phút.

---

## 🔧 Yêu cầu Hệ thống
- **Python**: 3.9+
- **Database**: PostgreSQL 14+ (có hỗ trợ JSONB)
- **Cấu hình tối thiểu**: RAM 16GB, Disk 50GB (cho dữ liệu OSM).

---
*Version 2.0 — Phát triển bởi Nguyễn Vũ Trọng Giang (MIS - 2470279)*
