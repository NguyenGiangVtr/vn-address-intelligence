# TODO: Fix mobile zoom effect for mapping-search-input in lookup smart filter

## ✅ Plan đã được approve
- [ ] **ui/controls-template.js**: add scoped class hook `smart-filter-search-input` to smart filter search textbox (`${prefix}-search-input`)
- [ ] **ui/style.css**: add mobile-safe rule for `.search-box-unified .smart-filter-search-input` with font-size 16px to prevent iOS auto-zoom
- [ ] Verify style remains consistent with current theme and no regression for existing smart filter inputs

**Current step:** Update `ui/controls-template.js`
