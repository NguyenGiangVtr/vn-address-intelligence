# Parser Display Fix - Entity Structure Issue

## Final Root Cause
Entity extraction đang ưu tiên sai field. PreLabeler entities có structure:
```javascript
{
  "value": {
    "labels": ["STR"],
    "text": "Ly Thuong Kiet"
  }
}
```

Nhưng code đang check `entity.label` trước (không tồn tại), sau đó mới check `entity.value?.labels?.[0]`.

## Final Fix

### Before (ui/app.js line ~4539)
```javascript
const label = entity.label || (entity.value?.labels?.[0]) || "";
const text = entity.text || (entity.value?.text) || "";
```

### After
```javascript
const label = entity.value?.labels?.[0] || entity.label || "";
const text = entity.value?.text || entity.text || "";
```

## Test Result
Với địa chỉ "268 Ly Thuong Kiet, Phuong Dien Hong, Ho Chi Minh":
- ✅ Entity 1: STR = "Ly Thuong Kiet"
- ✅ Entity 2: NUM = "268"
- ✅ Components extracted: { house_number: "268", street: "Ly Thuong Kiet" }
- ✅ Hero Output Card displays correctly

## All Changes Summary
1. Added `data-entity` and `data-text` to entity chips
2. Store prelabelerEntities in variable during fetch
3. Pass prelabelerEntities to _updateHeroOutputFromResults()
4. Extract from entities array instead of DOM
5. **Fix entity structure field priority** (value.labels before label)

## Files Changed
- `ui/app.js`: Complete entity extraction fix
