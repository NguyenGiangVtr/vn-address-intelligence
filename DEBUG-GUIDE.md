# Parser Display Issue - Complete Debug Guide

## Vấn đề
API trả về 200 OK nhưng Hero Output Card không hiển thị kết quả.

## Đã sửa (Summary)

### 1. API Layer (src/app/api/server.py)
- ✅ Thêm Pydantic model `ParserAnalyzeRequest`
- ✅ Fix loading state check
- ✅ Tắt auto-reload

### 2. UI Layer (ui/app.js)
- ✅ Lưu `prelabelerEntities` vào biến
- ✅ Truyền entities vào `_updateHeroOutputFromResults()`
- ✅ Fix entity structure priority: `entity.value?.labels?.[0]` trước
- ✅ Thêm debug logging
- ✅ Update version: app.js?v=202605201344

## Debug Steps

### Step 1: Test với debug file
```bash
# Mở file này trong browser
d:\2.GIT SOURCE\vn-address-intelligence\test-parser-debug.html

# Nhấn "Test Parser Flow"
# Xem Hero Output có hiển thị không
# Xem logs chi tiết
```

**Nếu test file HOẠT ĐỘNG** → Vấn đề là browser cache
**Nếu test file KHÔNG hoạt động** → Vấn đề là API response

### Step 2: Clear browser cache hoàn toàn
```
1. Mở http://localhost:8081
2. Nhấn F12 (mở DevTools)
3. Right-click vào nút Reload
4. Chọn "Empty Cache and Hard Reload"
5. Hoặc: Ctrl+Shift+Delete → Clear all browsing data
```

### Step 3: Kiểm tra Console logs
Mở Console (F12) và tìm các dòng sau:

**Logs mong đợi:**
```
[DEBUG] Starting Promise.all for models: [...]
[DEBUG] Processing prelabelerEntities: [...]
[DEBUG] Entity label: STR text: Ly Thuong Kiet
[DEBUG] Entity label: NUM text: 268
[DEBUG] Extracted components: {...}
[DEBUG] About to call _updateHeroOutputFromResults...
[DEBUG] Calling _updateHeroOutput with data: {...}
[DEBUG] Set heroOutput display to block
[DEBUG] _updateHeroOutputFromResults completed
```

**Nếu KHÔNG thấy logs:**
- Browser đang dùng cached version cũ
- Clear cache và reload lại

**Nếu thấy ERROR:**
- Copy toàn bộ error message
- Paste vào chat để debug

### Step 4: Kiểm tra Network tab
```
1. Mở Network tab (F12)
2. Nhấn "Phân tích"
3. Xem các request /api/parser/analyze
4. Kiểm tra:
   - Tất cả 5 models có trả về 200 không?
   - Response có outputs.prelabeler.result không?
   - prelabeler.result có entities không?
```

### Step 5: Kiểm tra Elements tab
```
1. Mở Elements tab (F12)
2. Tìm element: #parser-hero-output
3. Kiểm tra style:
   - display: block (ĐÚNG)
   - display: none (SAI - Hero Output bị ẩn)
```

## Possible Issues

### Issue 1: LLM Timeout
**Triệu chứng:** Status stuck ở "4/5 model hoàn thành"
**Nguyên nhân:** LLM model chạy quá chậm (>60s)
**Giải pháp:** Đợi hoặc skip LLM model

### Issue 2: Browser Cache
**Triệu chứng:** Không có debug logs trong Console
**Nguyên nhân:** Browser dùng cached app.js cũ
**Giải pháp:** Empty cache and hard reload

### Issue 3: Promise.all stuck
**Triệu chứng:** Không thấy "[DEBUG] All models completed"
**Nguyên nhân:** Một model bị hang
**Giải pháp:** Xem Network tab, model nào chưa complete

### Issue 4: Exception in update function
**Triệu chứng:** Thấy "[DEBUG] About to call..." nhưng không thấy "[DEBUG] Calling _updateHeroOutput"
**Nguyên nhân:** Exception trong _updateHeroOutputFromResults
**Giải pháp:** Xem Console errors (màu đỏ)

## Quick Test Command
```bash
# Test API trực tiếp
cd "d:\2.GIT SOURCE\vn-address-intelligence"
python test_prelabeler_structure.py
```

## Files Created for Debug
- `test-parser-debug.html` - Standalone test UI
- `test-parser-ui.html` - Simple API test
- `test_prelabeler_structure.py` - Python API test
- `test_all_models.py` - Test all models

## Next Action Required
**Paste vào chat:**
1. Console logs (toàn bộ)
2. Network tab screenshot (nếu có lỗi)
3. Kết quả test từ test-parser-debug.html
