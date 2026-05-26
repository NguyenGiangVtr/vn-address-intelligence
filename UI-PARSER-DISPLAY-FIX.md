# UI Parser Display Fix

## Vấn đề
Hero Output Card (`#parser-hero-output`) không hiển thị kết quả sau khi phân tích.

## Nguyên nhân
Hàm `_updateHeroOutputFromResults()` cố gắng extract data từ DOM elements bằng selector `span[data-entity]`, nhưng `_renderModelCard()` không tạo attribute `data-entity` khi render entity chips.

## Giải pháp

### 1. Thêm data attributes vào entity chips (ui/app.js line ~5030)
```javascript
// BEFORE:
return `<span class="pmodel-ent-chip" style="..." title="${lbl}">${lbl}: ${escapeHtml(txt)}</span>`;

// AFTER:
return `<span class="pmodel-ent-chip" data-entity="${lbl}" data-text="${escapeHtml(txt)}" style="..." title="${lbl}">${lbl}: ${escapeHtml(txt)}</span>`;
```

### 2. Cập nhật logic extract text (ui/app.js line ~4532)
```javascript
// BEFORE:
const text = span.textContent;

// AFTER:
const text = span.dataset.text || span.textContent.split(': ')[1] || span.textContent;
```

## Test
1. Reload browser (Ctrl+F5 để clear cache)
2. Nhập địa chỉ: "268 Lý Thường Kiệt, Phường Diên Hồng, Hồ Chí Minh"
3. Nhấn "Phân tích"
4. Hero Output Card sẽ hiển thị với:
   - Địa chỉ chuẩn hóa
   - Các thành phần (số nhà, đường, phường, tỉnh)
   - ACS score và decision
   - Thời gian xử lý

## Files đã sửa
- `ui/app.js`: Thêm data attributes và cập nhật extract logic
