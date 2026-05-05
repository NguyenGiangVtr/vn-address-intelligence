# Đề xuất Tái cấu trúc Dự án (Standardization)

## 1. Cấu trúc mới đề xuất

```text
vn-address-intelligence/
├── app/                        # Main Package (Đổi tên từ vn_address_intelligence)
│   ├── api/                    # FastAPI Routes & Models
│   │   └── server.py           # (Từ api.py)
│   ├── core/                   # Cấu hình & Kết nối DB
│   │   ├── config.py
│   │   └── database.py
│   ├── services/               # Logic nghiệp vụ (Crawlers, Fetchers)
│   │   ├── osm_fetcher.py
│   │   ├── gso_crawler.py
│   │   └── enrichment.py
│   ├── ai/                     # AI Research & Training (Từ top-level src/)
│   │   ├── models/             # PhoBERT, mGTE implementations
│   │   ├── pipeline.py
│   │   └── experiment.py
│   └── main.py                 # CLI Entry point
│
├── ui/                         # Frontend (Dashboard)
│   ├── assets/
│   ├── index.html
│   └── app.js
│
├── scripts/                    # Các kịch bản bảo trì & trích xuất
│   ├── export_evidence.py
│   └── seed_db.py
│
├── data/                       # Dữ liệu cục bộ (CSV, JSON, History)
├── docs/                       # Tài liệu hướng dẫn & Báo cáo
├── evidence/                   # File minh chứng đã trích xuất
├── logs/                       # Nhật ký hệ thống
└── requirements.txt
```

## 2. Các bước thực hiện
1. **Giai đoạn 1**: Tạo các thư mục mới (`app/api`, `app/core`, etc.).
2. **Giai đoạn 2**: Di chuyển file và cập nhật `import`.
   - Chuyển `api.py` -> `app/api/server.py`.
   - Chuyển `database.py`, `config.py` -> `app/core/`.
   - Chuyển AI scripts từ `src/` vào `app/ai/`.
3. **Giai đoạn 3**: Cập nhật file `.env` và các đường dẫn tĩnh trong `api/server.py`.
4. **Giai đoạn 4**: Xóa các thư mục thừa (`src/`, `ls_env/`, `assets/` nếu không dùng).

## 3. Lợi ích
- Tuân thủ chuẩn **Clean Architecture**.
- Dễ dàng mở rộng (Scalability) khi thêm các mô hình AI mới.
- Tách biệt rõ ràng giữa logic backend và nghiên cứu AI.
