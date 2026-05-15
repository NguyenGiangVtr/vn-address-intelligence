# 🔄 SUPA Benchmark Page - Refactor Plan

**Ngày:** 2026-05-16  
**Vấn đề:** Page SUPA có quá nhiều custom style, không tuân thủ chuẩn dự án

---

## ❌ Vấn đề hiện tại

### 1. **Quá nhiều custom CSS**
- Định nghĩa lại các biến CSS riêng (`--supa-accent`, `--supa-bg-card`, etc.)
- Custom padding/margin khác với các page khác
- Không sử dụng các class có sẵn của theme

### 2. **Không tuân thủ layout chuẩn**
- Các page khác: Dùng `.page` với padding mặc định từ `#page-content` (16px)
- SUPA page: Custom `supa-body` với padding 24px
- Không sử dụng `.page-header` chuẩn

### 3. **Quá nhiều margin/padding**
- `mb-24`, `mt-24`, `p-16`, `p-12` ở khắp nơi
- Làm mất không gian hiển thị data
- Không đồng bộ với các page khác

---

## ✅ Giải pháp

### 1. **Loại bỏ custom CSS variables**
```css
/* ❌ Không nên */
:root {
  --supa-accent: #6366f1;
  --supa-bg-card: var(--bg-surface);
}

/* ✅ Nên dùng */
/* Dùng trực tiếp var(--accent), var(--bg-surface) từ theme */
```

### 2. **Sử dụng layout chuẩn**
```html
<!-- ❌ Hiện tại -->
<div class="page" id="supa-bench">
  <div class="supa-sticky-header">...</div>
  <div class="supa-body" style="padding: 24px;">...</div>
</div>

<!-- ✅ Nên dùng -->
<div class="page" id="supa-bench">
  <!-- Stepper compact ở đầu -->
  <div style="margin-bottom: 16px;">...</div>
  
  <!-- Nội dung dùng class chuẩn -->
  <div class="page-header">
    <h2>Tiêu đề</h2>
    <p>Mô tả</p>
  </div>
  
  <div class="card">...</div>
</div>
```

### 3. **Giảm margin/padding**
```css
/* ❌ Hiện tại */
.mb-24 { margin-bottom: 24px; }
.mt-24 { margin-top: 24px; }
.p-16 { padding: 16px; }

/* ✅ Nên dùng */
/* Dùng spacing mặc định của card, page-header */
/* Chỉ thêm margin khi thực sự cần */
```

### 4. **Đơn giản hóa stepper**
```css
/* Chỉ giữ lại CSS tối thiểu cho stepper */
#supa-bench .supa-stepper {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

#supa-bench .supa-step {
  flex: 1;
  min-width: 80px;
  padding: 6px;
  cursor: pointer;
  border-radius: var(--radius-sm);
}

#supa-bench .supa-step-num {
  width: 24px;
  height: 24px;
  font-size: 12px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

#supa-bench .supa-step.is-active .supa-step-num {
  background: var(--accent);
  color: white;
}
```

---

## 📋 Checklist Refactor

### CSS
- [ ] Xóa tất cả custom CSS variables (`--supa-*`)
- [ ] Dùng theme variables: `var(--accent)`, `var(--bg-surface)`, `var(--text-primary)`
- [ ] Xóa `.supa-sticky-header`, `.supa-body`
- [ ] Giữ lại chỉ CSS cho stepper (tối thiểu)
- [ ] Xóa các custom `.supa-metric-card`, `.supa-hero-metric`
- [ ] Dùng `.card`, `.card-body`, `.card-header` có sẵn

### HTML Structure
- [ ] Xóa `<div class="supa-body">`
- [ ] Dùng `.page-header` cho tiêu đề mỗi tab
- [ ] Giảm `mb-24` → `mb-16` hoặc không dùng
- [ ] Giảm `mt-24` → `mt-16` hoặc không dùng
- [ ] Giảm `p-16` → dùng padding mặc định của `.card-body`
- [ ] Xóa các info box với custom background/border
- [ ] Dùng `.text-xs`, `.text-sm`, `.text-secondary` có sẵn

### Layout
- [ ] Page scroll tự nhiên (không cần custom scroll container)
- [ ] Stepper ở đầu page, không sticky
- [ ] Padding 16px từ `#page-content` (mặc định)
- [ ] Không custom height cho body

---

## 🎯 Kết quả mong đợi

### Trước
```
- 200+ dòng custom CSS
- Custom scroll container
- Custom padding/margin khắp nơi
- Không đồng bộ với các page khác
```

### Sau
```
- ~50 dòng CSS (chỉ cho stepper)
- Scroll tự nhiên như các page khác
- Padding/margin chuẩn (16px)
- Đồng bộ hoàn toàn với theme
```

---

## 📝 Ghi chú

1. **Ưu tiên:** Đơn giản > Đẹp
2. **Nguyên tắc:** Dùng class có sẵn > Tạo class mới
3. **Spacing:** Ít hơn > Nhiều hơn
4. **Consistency:** Giống các page khác > Độc đáo

---

**Tạo lúc:** 2026-05-16 00:57 UTC+7
