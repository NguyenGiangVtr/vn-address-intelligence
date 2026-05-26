# Parser Display Fix - Final Solution

## Root Cause
`_updateHeroOutputFromResults()` đang tìm `document.getElementById("presult-prelabeler")` nhưng element này **không tồn tại** trong HTML. PreLabeler chỉ render vào `#parser-output` (NER highlight zone), không có model card riêng.

## Solution

### 1. Store prelabeler entities in variable (ui/app.js ~line 4867)
```javascript
let prelabelerEntities = []; // Store prelabeler entities for hero output
```

### 2. Save entities when fetching prelabeler (ui/app.js ~line 4908)
```javascript
if (key === "prelabeler" && !firstNERDone) {
  firstNERDone = true;
  const entities = out?.result || [];
  prelabelerEntities = entities; // Save for hero output
  renderNERHighlight(entities);
}
```

### 3. Pass entities to update function (ui/app.js ~line 4940)
```javascript
_updateHeroOutputFromResults(lastMeta, totalMs, prelabelerEntities);
```

### 4. Extract from entities array instead of DOM (ui/app.js ~line 4499)
```javascript
function _updateHeroOutputFromResults(lastMeta, totalMs, prelabelerEntities = []) {
  // ...
  if (prelabelerEntities && prelabelerEntities.length > 0) {
    prelabelerEntities.forEach(entity => {
      const label = entity.label || (entity.value?.labels?.[0]) || "";
      const text = entity.text || (entity.value?.text) || "";
      
      if (label === "NUM") components.house_number = text;
      else if (label === "STR") components.street = text;
      else if (label === "WDS") components.ward.name = text;
      else if (label === "DST") components.district = text;
      else if (label === "PRO") components.province.name = text;
    });
  }
}
```

## Expected Result
Sau khi reload và test:
- ✅ Hero Output Card hiển thị
- ✅ Địa chỉ chuẩn hóa
- ✅ Các thành phần (số nhà, đường, phường, tỉnh)
- ✅ ACS score và decision
- ✅ Thời gian xử lý

## Files Changed
- `ui/app.js`: Fixed prelabeler entities extraction logic
