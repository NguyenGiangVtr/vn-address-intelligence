# ✅ SUPA Benchmark UI - Cải tiến Bước 3 và Flow hoàn chỉnh

**Ngày:** 2026-05-15  
**Thời gian:** 22:09 UTC+7

---

## 📋 Các vấn đề đã được giải quyết (Lần 2)

### ✅ 1. Làm rõ Phương án 1: Nhập kết quả từ Pipeline ngoại vi

**Vấn đề ban đầu:**
- Không rõ file CSV từ đâu
- Không hiểu phải làm gì với file CSV sau khi tải về
- Thiếu hướng dẫn quy trình

**Giải pháp:**
- Đổi tên: "Nhập kết quả thủ công (CSV)" → **"Nhập kết quả từ Pipeline ngoại vi"**
- Thêm info box với quy trình 4 bước rõ ràng:
  ```
  📋 Quy trình:
  1️⃣ Tải file CSV từ Bước 2 (nút "Tải CSV cho Pipeline ngoại vi")
  2️⃣ Chạy pipeline chuẩn hóa của bạn (Python script, API riêng, v.v.)
  3️⃣ Điền kết quả vào cột pred_standardized
  4️⃣ Upload file CSV đã điền kết quả ở form bên dưới
  ```
- Nhấn mạnh: File phải có cột `specimen_id` và `pred_standardized` **đã được điền**

---

### ✅ 2. Giải thích rõ "Chế độ Test" và "Bỏ qua Latency"

**Trước:**
```
☐ Chế độ Test
☐ Bỏ qua Latency
```
(Không có mô tả gì)

**Sau:**

#### Chế độ Test (Dry Run)
```
☐ Chế độ Test (Dry Run) ⓘ

Kiểm tra định dạng file mà không lưu vào database. 
Dùng để validate trước khi import thật.
```
- **Tooltip:** "Kiểm tra file CSV mà không lưu vào database. Dùng để validate format trước khi import thật."
- **Mục đích:** Test xem file CSV có đúng format không trước khi import thật
- **Khi nào dùng:** Lần đầu import, hoặc khi không chắc file đúng format

#### Bỏ qua Latency
```
☐ Bỏ qua Latency ⓘ

Không đo thời gian import. Chỉ bật nếu file CSV của bạn 
đã có cột latency_ms từ pipeline.
```
- **Tooltip:** "Không đo thời gian xử lý khi import. Chỉ dùng khi file CSV đã có cột latency_ms."
- **Mục đích:** Tắt việc đo latency tự động nếu file CSV đã có sẵn cột `latency_ms`
- **Khi nào dùng:** Khi pipeline của bạn đã export latency trong CSV

---

### ✅ 3. Làm rõ Phương án 2: Tự động chạy Pipeline

**Vấn đề ban đầu:**
- Không hiểu phương án này hoạt động như thế nào
- Không có button để click
- Không biết cách kích hoạt

**Giải pháp:**

#### Thêm hướng dẫn chi tiết:
```
⚡ Chế độ Tự động (Ablation Study)

Pipeline AI sẽ tự động chạy trên server ngay sau khi tạo bộ thử ở Bước 1.

🔧 Cách kích hoạt:
1️⃣ Quay lại Bước 1
2️⃣ Tích vào checkbox "TỰ ĐỘNG CHẠY NORMALIZATION"
3️⃣ Chọn các thành phần model (NER, Retrieval, LLM)
4️⃣ Click "Bắt đầu Workflow"
5️⃣ Hệ thống sẽ tự động: Extract → Normalize → Eval
```

#### Thêm button "Quay lại Bước 1 để cấu hình"
- Click vào button sẽ tự động chuyển về Tab 1

#### Liệt kê ưu điểm:
```
✅ Ưu điểm của Phương án 2:
• Không cần tải file CSV thủ công
• Không cần chạy pipeline riêng
• Tự động đo latency chính xác
• Phù hợp cho ablation study (so sánh các cấu hình model)
```

---

### ✅ 4. Sửa lỗi tràn chiều rộng (overflow)

**Vấn đề:**
- Controls trong Bước 3 bị tràn ra ngoài màn hình
- Không thể nhìn thấy toàn bộ nội dung

**Giải pháp:**
```css
/* Thay vì dùng class grid-cols-2 */
<div class="grid grid-cols-2 gap-24">

/* Dùng inline style với overflow control */
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 100%; overflow: hidden;">
  <div class="card" style="min-width: 0;">
    <!-- Content với max-width: 100% trên tất cả inputs -->
  </div>
</div>
```

**Các thay đổi cụ thể:**
- Thêm `max-width: 100%; overflow: hidden;` cho container
- Thêm `min-width: 0;` cho các card (ngăn flex item overflow)
- Thêm `max-width: 100%;` cho tất cả input fields
- Thêm `word-wrap: break-word; white-space: pre-wrap;` cho console log

---

### ✅ 5. Thêm Flow Demo hoàn chỉnh

**Vấn đề:**
- Người dùng không có file CSV để test
- Không thể trải nghiệm flow hoàn chỉnh

**Giải pháp:**

#### A. Thêm hướng dẫn 2 luồng ở Bước 2:
```
🎯 Bạn có 2 lựa chọn để tiếp tục:

┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ 🔄 Luồng Ngoại vi (Manual)      │  │ ⚡ Luồng Tự động (Auto)         │
├─────────────────────────────────┤  ├─────────────────────────────────┤
│ 1. Click nút "Tải CSV"          │  │ 1. Quay lại Bước 1              │
│ 2. Chạy pipeline của bạn        │  │ 2. Tích "TỰ ĐỘNG CHẠY..."      │
│ 3. Điền kết quả vào CSV         │  │ 3. Chọn cấu hình model          │
│ 4. Sang Bước 3 → Upload CSV     │  │ 4. Click "Bắt đầu Workflow"     │
│                                 │  │ 5. Tự động chạy → Bước 4        │
└─────────────────────────────────┘  └─────────────────────────────────┘

💡 Gợi ý: Nếu chỉ muốn xem demo nhanh, dùng Luồng Tự động. 
         Nếu muốn test model riêng, dùng Luồng Ngoại vi.
```

#### B. Thêm nút "Import Demo" ở Bước 3:
```
🧪 Chế độ Demo (Không có file CSV?)

Nếu bạn chưa có file CSV kết quả, có thể dùng chế độ demo để test flow. 
Hệ thống sẽ tự động copy dữ liệu tham chiếu V2 làm kết quả (EM = 100%).

[🎭 Import Demo (Copy từ ref_address_v2)]
```

**Cách hoạt động:**
1. Click nút "Import Demo"
2. Confirm dialog giải thích rõ đây là demo (EM = 100%)
3. Gọi API workflow với `preds_demo_ref_v2: true`
4. Tự động chuyển sang Bước 4 để xem kết quả

---

## 📁 Files đã thay đổi (Lần 2)

1. **ui/pages/supa-bench.html**
   - Redesign toàn bộ Tab 3 với 2 phương án rõ ràng
   - Thêm quy trình 4 bước cho Phương án 1
   - Thêm hướng dẫn chi tiết cho Phương án 2
   - Thêm tooltips và mô tả cho checkboxes
   - Thêm nút "Import Demo"
   - Thêm flow guide ở Tab 2
   - Fix overflow issues với inline styles

2. **ui/app.js**
   - Thêm event handler cho nút "Import Demo"
   - Confirm dialog trước khi import demo
   - Tự động chuyển sang Tab 4 sau import demo

---

## 🎯 Flow hoàn chỉnh (3 cách)

### Cách 1: Luồng Tự động (Nhanh nhất - Dành cho demo)
```
Bước 1: Tích "TỰ ĐỘNG CHẠY NORMALIZATION" → Click "Bắt đầu Workflow"
        ↓
Bước 2: (Tự động skip)
        ↓
Bước 3: (Tự động chạy pipeline)
        ↓
Bước 4: Xem kết quả ✅
```

### Cách 2: Luồng Demo Import (Test flow nhanh)
```
Bước 1: Click "Bắt đầu Workflow" (không tích auto)
        ↓
Bước 2: Xem dữ liệu mẫu
        ↓
Bước 3: Click "🎭 Import Demo" → Confirm
        ↓
Bước 4: Xem kết quả (EM = 100%) ✅
```

### Cách 3: Luồng Ngoại vi (Dành cho test model thật)
```
Bước 1: Click "Bắt đầu Workflow"
        ↓
Bước 2: Click "📥 Tải CSV cho Pipeline ngoại vi"
        ↓
        (Chạy pipeline của bạn, điền kết quả vào CSV)
        ↓
Bước 3: Upload CSV → Click "📤 Tải lên & Xử lý"
        ↓
Bước 4: Xem kết quả ✅
```

---

## 🧪 Testing Checklist (Lần 2)

### Tab 3 - Phương án 1
- [x] Hiển thị quy trình 4 bước rõ ràng ✅
- [x] Tooltip "Chế độ Test" giải thích đúng ✅
- [x] Tooltip "Bỏ qua Latency" giải thích đúng ✅
- [x] Nút "Import Demo" hoạt động ✅
- [x] Confirm dialog hiển thị trước khi demo import ✅
- [x] Không bị overflow trên màn hình nhỏ ✅

### Tab 3 - Phương án 2
- [x] Hướng dẫn 5 bước rõ ràng ✅
- [x] Nút "Quay lại Bước 1" hoạt động ✅
- [x] Liệt kê ưu điểm của phương án 2 ✅
- [x] Console log không bị overflow ✅

### Tab 2 - Flow Guide
- [x] Hiển thị 2 luồng song song ✅
- [x] Gợi ý rõ ràng khi nào dùng luồng nào ✅
- [x] Nút "Tải CSV" có icon rõ ràng ✅

### Flow hoàn chỉnh
- [x] Cách 1 (Auto): Tích checkbox → Workflow → Kết quả ✅
- [x] Cách 2 (Demo): Workflow → Import Demo → Kết quả ✅
- [x] Cách 3 (Manual): Workflow → Tải CSV → Upload → Kết quả ✅

---

## 📊 So sánh Trước/Sau

### Trước (Tab 3)
```
❌ Không rõ file CSV từ đâu
❌ Không biết phải làm gì với file
❌ Checkbox không có mô tả
❌ Phương án 2 không có button
❌ Bị overflow trên màn hình nhỏ
❌ Không có cách test nhanh
```

### Sau (Tab 3)
```
✅ Quy trình 4 bước rõ ràng
✅ Hướng dẫn chi tiết từng bước
✅ Tooltip giải thích đầy đủ
✅ Nút "Quay lại Bước 1" rõ ràng
✅ Responsive, không overflow
✅ Có nút "Import Demo" để test
✅ Flow guide ở Bước 2
```

---

## 🎨 Visual Preview (Tab 3)

```
┌─────────────────────────────────────────────────────────────────┐
│ Bước 3: Chuẩn hóa Địa chỉ                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📥 Input: noisy_raw_address                                 │ │
│ │ 📤 Output: pred_standardized → DB → Bước 4                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│ │ Phương án 1: Ngoại vi    │  │ Phương án 2: Tự động         │ │
│ ├──────────────────────────┤  ├──────────────────────────────┤ │
│ │ ┌──────────────────────┐ │  │ ⚡ Chế độ Tự động            │ │
│ │ │ 📋 Quy trình:        │ │  │                              │ │
│ │ │ 1️⃣ Tải CSV từ Bước 2 │ │  │ 🔧 Cách kích hoạt:          │ │
│ │ │ 2️⃣ Chạy pipeline     │ │  │ 1️⃣ Quay lại Bước 1          │ │
│ │ │ 3️⃣ Điền kết quả      │ │  │ 2️⃣ Tích checkbox            │ │
│ │ │ 4️⃣ Upload CSV        │ │  │ 3️⃣ Chọn model               │ │
│ │ └──────────────────────┘ │  │ 4️⃣ Bắt đầu Workflow         │ │
│ │                          │  │                              │ │
│ │ [Chọn file CSV]          │  │ [← Quay lại Bước 1]         │ │
│ │ [Mô tả nguồn *]          │  │                              │ │
│ │                          │  │ ✅ Ưu điểm:                  │ │
│ │ ☐ Chế độ Test ⓘ          │  │ • Không cần CSV thủ công    │ │
│ │ ☐ Bỏ qua Latency ⓘ       │  │ • Tự động đo latency        │ │
│ │                          │  │ • Phù hợp ablation study    │ │
│ │ [📤 Tải lên & Xử lý]     │  │                              │ │
│ │                          │  │ [Console Log]                │ │
│ │ 🧪 Chế độ Demo           │  │                              │ │
│ │ [🎭 Import Demo]         │  │                              │ │
│ └──────────────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment

Tất cả thay đổi đã sẵn sàng:
```bash
git add ui/pages/supa-bench.html ui/app.js
git commit -m "feat(ui): complete SUPA workflow with 3 paths

- Add detailed 4-step process guide for manual CSV import
- Add tooltips explaining 'Dry Run' and 'Skip Latency' options
- Add clear instructions for auto-pipeline activation
- Add 'Import Demo' button for quick testing (EM=100%)
- Add flow guide in Step 2 showing 2 paths (manual vs auto)
- Fix overflow issues in Step 3 (responsive layout)
- Enable complete workflow: Auto / Demo / Manual

Users can now:
1. Auto: Enable checkbox in Step 1 → Auto normalize → Results
2. Demo: Create run → Import Demo → Results (test flow)
3. Manual: Download CSV → Run pipeline → Upload → Results"
```

---

## 📝 Ghi chú quan trọng

1. **Import Demo chỉ dùng để test flow**, không phải kết quả thật
2. **Chế độ Test (Dry Run)** không lưu vào DB, chỉ validate format
3. **Bỏ qua Latency** chỉ bật khi CSV đã có cột `latency_ms`
4. **Phương án 2** phải được kích hoạt từ Bước 1, không có button riêng ở Bước 3

**Hoàn tất lúc:** 2026-05-15 22:09 UTC+7
