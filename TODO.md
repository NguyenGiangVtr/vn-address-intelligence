# UI Layout Refactor - 3-Zone Standard (parser.html)

## ✅ Planning Complete
- [x] Analyzed parser.html standard (hero→stats→main)
- [x] Reviewed style.css theme system  
- [x] Searched all ui/pages/*.html patterns
- [x] User approved plan

## 🔄 Implementation Steps

### Phase 1: Infrastructure (Current)
- [x] Create ui/style.css `.page-hero` utility class
- [ ] Refactor ui/pages/experiments.html → 3-zone
- [ ] Refactor ui/pages/batch.html → 3-zone  
- [ ] Refactor ui/pages/overview.html → 3-zone

### Phase 2: Core Pages
- [ ] ui/pages/training.html
- [ ] ui/pages/label-studio.html  
- [ ] ui/pages/ward-mapper.html
- [ ] ui/pages/osm-enrichment.html

### Phase 3: Admin/Utility
- [ ] ui/pages/settings.html
- [ ] ui/pages/nso-sync.html
- [ ] ui/pages/admin-units.html
- [ ] ui/pages/lookup.html

### Phase 4: Complete & Test
- [ ] ui/app.js selector updates if needed
- [ ] Browser test responsive layout
- [ ] Final cleanup + attempt_completion

**Standard per page**: 
1. `.page-hero` (actions/filters horizontal) 
2. `.stats-grid` OR model cards (if applicable)
3. Main `.card` w/ `.card-body` flex:1 (table/grid/log/output)
