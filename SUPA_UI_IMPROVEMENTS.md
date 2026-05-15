# SUPA Benchmark UI Improvements

**Date:** 2026-05-15  
**Files Modified:**
- `ui/pages/supa-bench.html`
- `ui/app.js`

## Changes Summary

### 1. ✅ Redesigned Metric Cards Color Scheme

**Location:** Tab 4 - Results section

#### Before:
- Exact Match (V2): Purple accent (`--supa-accent`)
- Exact Match (V1): Green (`--supa-success`)
- Latency: Orange

#### After:
- **Exact Match (V2)**: Green gradient (`#10b981` → `#059669`)
  - Border: `#10b981` (emerald green)
  - Background: Subtle green gradient
  - Description: "Tỉ lệ khớp 100% với tham chiếu mới nhất"
  
- **Exact Match (V1)**: Blue gradient (`#3b82f6` → `#2563eb`)
  - Border: `#3b82f6` (blue)
  - Background: Subtle blue gradient
  - Description: "Tỉ lệ khớp với địa chỉ cũ (legacy)"
  
- **Latency (Mean)**: Orange gradient (`#f59e0b` → `#d97706`)
  - Border: `#f59e0b` (amber)
  - Background: Subtle orange gradient
  - Description: "Thời gian xử lý trung bình mỗi địa chỉ"

**Rationale:**
- Green for V2 emphasizes it as the primary/current metric
- Blue for V1 indicates legacy/historical data
- Orange for latency follows performance metric conventions

---

### 2. ✅ Fixed Tab Navigation Bug

**Issue:** Clicking on Stage 3 (Chuẩn hóa) would incorrectly show Stage 1 content.

**Root Cause:** The `handleRunResponse()` function was automatically calling `switchTab(2)` after loading specimens, which interfered with manual tab navigation.

**Solution:**
- Added `autoSwitchTab` parameter to `handleRunResponse()` (default: `true`)
- Only auto-switch to tab 2 when creating new runs (user-initiated workflow)
- Removed auto-switch behavior from:
  - Manual run selection (dropdown change)
  - Refresh button click
  - Eval button click
- Added smart auto-switch after import: goes to tab 4 (Results) to show evaluation

**Code Changes:**
```javascript
// Before
const handleRunResponse = async (j) => {
  // ... load data ...
  switchTab(2); // Always switched to tab 2
};

// After
const handleRunResponse = async (j, autoSwitchTab = true) => {
  // ... load data ...
  if (autoSwitchTab) {
    switchTab(2); // Only when explicitly requested
  }
};
```

---

### 3. ✅ Improved Status Bar & Progress Indicator

**Location:** Sticky header mini-log console

#### Before:
```
● STATUS: Đã chọn bộ thử. 75%
```
- Unclear what "STATUS" means
- Percentage (75%) was ambiguous - percentage of what?

#### After:
```
● Đã chọn bộ thử.                    Tiến độ workflow  3/4
```
- Removed redundant "STATUS:" label
- Changed progress from percentage to step counter: `X/4` format
- Added label "Tiến độ workflow" to clarify meaning
- Better visual separation with flex layout

**Implementation:**
```javascript
// Progress calculation
const completed = Math.floor(progress / 25); // 0%, 25%, 50%, 75%, 100% → 0, 1, 2, 3, 4
progressEl.textContent = `${completed}/4`;
```

**HTML Structure:**
```html
<div class="supa-mini-log">
  <div class="flex items-center gap-8 overflow-hidden" style="flex: 1;">
    <span style="color: var(--supa-accent);">●</span>
    <span class="log-msg" id="supa-mini-log-msg">...</span>
  </div>
  <div class="flex items-center gap-12">
    <span id="supa-mini-progress-label">Tiến độ workflow</span>
    <div id="supa-mini-progress-text">0/4</div>
  </div>
</div>
```

---

### 4. ✅ Added Input/Output Descriptions for Each Stage

**Purpose:** Help users understand data flow between stages

#### Stage 1: Khởi tạo (Initialization)
```
📥 Input: Dữ liệu từ bảng prq.ground_truth (địa chỉ đã được kiểm chứng)
📤 Output: Bộ dữ liệu thử nghiệm với nhiễu được lưu vào prq.supa_benchmark_specimen
```

#### Stage 2: Dữ liệu mẫu (Sample Data)
```
📥 Input: Dữ liệu từ Bước 1 (bộ thử đã được tạo)
📤 Output: File CSV có thể tải xuống để chạy pipeline chuẩn hóa bên ngoài, 
          hoặc tiếp tục sang Bước 3 để chuẩn hóa
```

#### Stage 3: Chuẩn hóa (Normalization)
```
📥 Input: Dữ liệu nhiễu từ Bước 2 (cột noisy_raw_address)
📤 Output: Địa chỉ đã chuẩn hóa (cột pred_standardized) được lưu vào DB 
          để đánh giá ở Bước 4
```

#### Stage 4: Kết quả (Results)
```
📥 Input: Kết quả chuẩn hóa từ Bước 3 + Dữ liệu tham chiếu (V1 & V2)
📤 Output: Các chỉ số đánh giá (Exact Match, F1-Score, Latency) và báo cáo so sánh
```

**Visual Design:**
- Info boxes with colored left border matching stage theme
- Monospace font for technical terms (table/column names)
- Clear emoji indicators (📥 Input, 📤 Output)

---

## Testing Checklist

- [ ] Click on each stage (1, 2, 3, 4) - verify correct tab displays
- [ ] Create new run - should auto-switch to Stage 2
- [ ] Select existing run from dropdown - should stay on current tab
- [ ] Import predictions CSV - should auto-switch to Stage 4
- [ ] Click "Tính toán lại Metrics" - should stay on Stage 4
- [ ] Verify progress indicator shows "0/4", "1/4", "2/4", "3/4", "4/4"
- [ ] Check metric card colors: V2=green, V1=blue, Latency=orange
- [ ] Verify input/output descriptions are visible on all stages

---

## Browser Compatibility

All changes use standard CSS and JavaScript features:
- CSS Grid & Flexbox (widely supported)
- CSS custom properties (IE11+)
- ES6 arrow functions (modern browsers)
- No new dependencies added

---

## Future Improvements (Optional)

1. Add tooltips on hover for metric cards explaining calculation method
2. Animate progress indicator transitions
3. Add keyboard shortcuts for tab navigation (1, 2, 3, 4 keys)
4. Export results as PDF report
5. Add dark/light theme toggle for metric cards
