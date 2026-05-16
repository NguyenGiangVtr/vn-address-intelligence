# SUPA Benchmark UI - Testing Guide

**Date:** 2026-05-16  
**Version:** 2.0

## Các vấn đề đã sửa

### 1. Console Log Improvements
- ✅ Tăng kích thước console từ 140px → 300-400px
- ✅ Loại bỏ scroll ngang (overflow-x: hidden)
- ✅ Text tự xuống dòng (white-space: pre-wrap)
- ✅ Hiển thị pipeline_stdout và pipeline_stderr riêng biệt
- ✅ Font size tăng từ 10px → 11px

### 2. Button "Chạy chuẩn hóa" ở Tab 2
- ✅ Thêm button primary "Chạy chuẩn hóa" 
- ✅ Tự động chuyển sang Tab 3 để xem console
- ✅ Chạy pipeline với cấu hình mặc định (NER + Retrieval mGTE + LLM)

### 3. Workflow Backend Integration
- ✅ Backend hỗ trợ `run_normalization: true`
- ✅ Tự động chạy production_pipeline.py
- ✅ Tự động eval sau khi pipeline xong
- ✅ Log đầy đủ stdout/stderr từ pipeline

---

## Hướng dẫn Test Full Flow

### Chuẩn bị
1. Đảm bảo server đang chạy: `python -m app.api.server`
2. Đảm bảo `.env` có: `SUPA_BENCHMARK_UI_ACTIONS=1`
3. Mở trình duyệt và vào trang SUPA Benchmark

---

## Flow 1: Tự động chạy Pipeline (Khuyến nghị)

### **Tab 1: Khởi tạo**
1. Click button **"Tạo mới"**
2. Điền thông tin:
   - Số lượng mẫu: `100` (test nhanh) hoặc `1000` (full test)
   - Seed: để trống (auto)
   - Profile Nhiễu: `SUP-1.0.0`
   - Ghi chú: để trống (auto)
3. ✅ **Tích checkbox "Tự động chạy Pipeline"**
4. Cấu hình Pipeline:
   - ✅ NER
   - ✅ Retrieval
   - ✅ LLM
   - Retriever: `mGTE` (mặc định)
5. Click **"Bắt đầu"**

**Kết quả mong đợi:**
- Loading overlay hiển thị
- Tự động chuyển sang Tab 2
- Console log hiển thị:
  - Extract output
  - Pipeline output (NER, Retrieval, LLM progress)
  - Eval output

### **Tab 2: Dữ liệu**
- Xem bảng specimens với dữ liệu nhiễu
- Cột "Dự đoán" sẽ có giá trị sau khi pipeline chạy xong
- Cột "Trạng thái" hiển thị match/mismatch

### **Tab 3: Chuẩn hóa**
- Console log hiển thị đầy đủ:
  - `[timestamp] workflow`
  - `[timestamp] Pipeline Output` ← MỚI!
  - `[timestamp] Eval Output` ← MỚI!
- Console cao 300-400px, không scroll ngang

### **Tab 4: Kết quả**
1. Click **"Tính toán"** (nếu cần refresh metrics)
2. Xem metrics:
   - Hero cards: EM (V2), EM (V1), Latency
   - Chi tiết độ chính xác: F1 scores cho đường/phường/quận/tỉnh
   - Latency P95, P99
   - Throughput
3. So sánh với Benchmark

---

## Flow 2: Chạy Pipeline từ Tab 2 (Mới)

### **Tab 1: Khởi tạo**
1. Click **"Tạo mới"**
2. Điền số lượng mẫu: `100`
3. **KHÔNG** tích "Tự động chạy Pipeline"
4. Click **"Chỉ trích mẫu"**

**Kết quả:** Chỉ extract specimens, không chạy pipeline

### **Tab 2: Dữ liệu**
1. Xem bảng specimens (cột "Dự đoán" trống)
2. Click button **"Chạy chuẩn hóa"** ← MỚI!
3. Confirm dialog xuất hiện
4. Click "Đồng ý"

**Kết quả mong đợi:**
- Tự động chuyển sang Tab 3
- Console log hiển thị pipeline progress
- Sau khi xong, quay lại Tab 2 để xem kết quả

---

## Flow 3: Demo Mode (Test nhanh)

### **Tab 1: Khởi tạo**
1. Tạo run mới với 100 specimens
2. Không tích "Tự động chạy Pipeline"
3. Click "Chỉ trích mẫu"

### **Tab 3: Chuẩn hóa**
1. Scroll xuống phần "Demo Mode"
2. Click **"Import Demo"**
3. Confirm dialog

**Kết quả:**
- Copy ref_v2 vào pred_standardized
- EM (V2) = 100%
- Tự động chuyển sang Tab 4

---

## Flow 4: Import CSV thủ công

### **Tab 2: Dữ liệu**
1. Click **"Tải CSV"**
2. Lưu file CSV

### Chạy pipeline bên ngoài (nếu cần)
```bash
python -m app.ai.production_pipeline --supa-run-id <RUN_ID> --limit 100
```

### **Tab 3: Chuẩn hóa**
1. Chọn file CSV đã xử lý
2. Điền "Mô tả nguồn": `Model V3 Test`
3. Click **"Tải lên"**

**Kết quả:**
- Import predictions vào database
- Tự động chuyển sang Tab 4

---

## Checklist Kiểm tra

### UI/UX
- [ ] Checkbox và radio button có khoảng cách với text
- [ ] Checkbox có checkmark (✓) khi checked
- [ ] Radio button có dot khi checked
- [ ] Console không scroll ngang
- [ ] Console cao đủ để xem log (300-400px)
- [ ] Stepper hiển thị đúng trạng thái (done/active/disabled)
- [ ] Status bar cập nhật đúng (0/4 → 4/4)

### Chức năng
- [ ] Tab 1: Tạo run mới thành công
- [ ] Tab 1: "Tự động chạy Pipeline" hoạt động
- [ ] Tab 2: Hiển thị specimens đúng
- [ ] Tab 2: Button "Chạy chuẩn hóa" hoạt động
- [ ] Tab 2: Tải CSV thành công
- [ ] Tab 3: Console log hiển thị đầy đủ
- [ ] Tab 3: Pipeline output hiển thị riêng biệt
- [ ] Tab 3: Import CSV thành công
- [ ] Tab 3: Demo mode hoạt động
- [ ] Tab 4: Metrics hiển thị đúng format
- [ ] Tab 4: Không có "100.00%%" hoặc "3.40% ms"
- [ ] Tab 4: So sánh benchmark hoạt động

### Performance
- [ ] Extract 100 specimens < 5s
- [ ] Pipeline 100 specimens < 2 phút
- [ ] Eval < 5s
- [ ] UI responsive, không lag

---

## Lỗi thường gặp

### 1. "Pipeline failed with code 1"
**Nguyên nhân:** Backend không thể chạy production_pipeline.py

**Giải pháp:**
- Kiểm tra `.env` có đủ config không (OPENAI_API_KEY, etc.)
- Kiểm tra database connection
- Xem log chi tiết trong console

### 2. Console không hiển thị pipeline output
**Nguyên nhân:** Backend trả về nhưng UI không log

**Giải pháp:**
- Đã sửa trong version này
- Refresh trình duyệt để load code mới

### 3. "SUPA benchmark UI actions are disabled"
**Nguyên nhân:** Thiếu env variable

**Giải pháp:**
```bash
# Thêm vào .env
SUPA_BENCHMARK_UI_ACTIONS=1
```

### 4. Metrics hiển thị "100.00%%"
**Nguyên nhân:** Format lỗi trong code cũ

**Giải pháp:**
- Đã sửa trong version này
- Bây giờ hiển thị "100.00%"

---

## Kết quả mong đợi

### Console Log (Tab 3)
```
[2026-05-16T02:35:47Z] workflow
{
  "exit_code": 0,
  "stdout": "SUPA extract OK: run_id=79...",
  "last_run_id_hint": 79,
  "ok": true
}

[2026-05-16T02:36:00Z] Pipeline Output
Processing 100 specimens...
NER: 100/100 done
Retrieval (mGTE): 100/100 done
LLM: 100/100 done
Saved predictions to database

[2026-05-16T02:36:15Z] Eval Output
Evaluating run_id=79...
EM (V2): 85.5%
EM (V1): 82.3%
F1 Duong: 92.1%
...
```

### Metrics (Tab 4)
```
EM (V2): 85.5%
EM (V1): 82.3%
Latency: 245 ms

Chi tiết độ chính xác:
- Độ đúng phần tên đường: 92.10%
- Độ đúng phần phường / xã: 88.50%
- Độ đúng phần quận / huyện: 91.20%
- Độ đúng phần tỉnh / thành phố: 95.80%
- Độ trễ mức 95%: 380.50 ms
- Độ trễ mức 99%: 520.30 ms
- Số địa chỉ xử lý mỗi giây: 4.08
```

---

## Notes

- Test với 100 specimens trước để nhanh
- Full test với 1000 specimens để đảm bảo performance
- Console log giờ đã hiển thị đầy đủ pipeline output
- Không cần chạy script bên ngoài nữa, tất cả trong UI

**Version 2.0 - Ready for Production Testing! 🚀**
