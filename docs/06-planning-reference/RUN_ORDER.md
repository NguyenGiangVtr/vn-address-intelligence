# 🚀 Hướng dẫn Vận hành Hệ thống Chuẩn hóa Địa chỉ

Chào bạn! Để hệ thống hoạt động chính xác nhất, hãy thực hiện theo đúng thứ tự 4 bước dưới đây:

---

### Bước 0: Chuẩn bị Môi trường (Chỉ làm 1 lần)
Mở terminal và cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

---

### Bước 1: Tiền xử lý bằng SQL (Tốc độ cực nhanh)
Mục tiêu: Dùng logic SQL để bóc tách phần "Lõi" (Số nhà + Tên đường) vào cột `street_address`.

1. Mở công cụ quản lý DB (DBeaver, Navicat, pgAdmin...).
2. Chạy nội dung file: `docs/update_address_smart.sql`.
3. Thực thi câu lệnh để bắt đầu bóc tách:
   ```sql
   SELECT scm.update_address_smart();
   ```

---

### Bước 2: Gán nhãn dữ liệu (Dành cho Team Data)
Mục tiêu: Giúp AI (NER) học cách phân biệt Số nhà, Tên đường, Tòa nhà.

1. **Export dữ liệu**:
   ```bash
   python src/export_for_annotation.py --limit 5000
   ```
2. **Gán nhãn**: Gửi file `data/ner_samples.json` cho Team Data để gán nhãn trên Label Studio.
3. **Huấn luyện AI** (Sau khi gán nhãn xong):
   ```bash
   python src/train_ner.py
   ```

---

### Bước 3: Chạy Pipeline chuẩn hóa tự động (Bước quan trọng nhất)
Mục tiêu: Sử dụng sức mạnh tổng hợp của AI (NER + LLM) để làm sạch và chuẩn hóa địa chỉ cuối cùng.

**Chạy thử nghiệm 100 dòng đầu tiên:**
```bash
python src/production_pipeline.py --config src/config.yaml --limit 100
```

**Chạy cho toàn bộ database:**
```bash
python src/production_pipeline.py --config src/config.yaml
```

---

### Bước 4: Kiểm tra kết quả
Bạn có thể kiểm tra kết quả ngay trong bảng `scm.address` bằng câu lệnh SQL:
```sql
SELECT 
    raw_address, 
    street_address, 
    address_standardized, 
    confidence_score, 
    processing_method 
FROM scm.address 
WHERE address_standardized IS NOT NULL 
ORDER BY id DESC;
```

---
**💡 Lưu ý:** 
- Trong khi đợi Team Data gán nhãn (Bước 2), bạn **vẫn có thể chạy Bước 3 ngay lập tức**. Hệ thống sẽ tự động dùng bộ lọc Regex thông minh để bóc tách tạm thời cho đến khi bạn có model AI chính thức.
