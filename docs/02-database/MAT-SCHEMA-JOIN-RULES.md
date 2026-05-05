# 🔗 MAT Schema Join Rules - Admin Version Consistency

**Created:** 2026-05-05  
**Priority:** CRITICAL  
**Applies to:** All queries joining mat.ward, mat.district, mat.province

---

## 🚨 **MANDATORY RULE: Admin Version Consistency**

### **Rule Statement:**
> **ALL joins with mat schema tables MUST include admin_version equality conditions to ensure temporal data consistency.**

### **Standard Join Pattern:**
```sql
FROM mat.ward w
JOIN mat.district d ON w.district_id = d.district_id 
    AND d.admin_version = w.admin_version
JOIN mat.province p ON d.province_id = p.province_id 
    AND p.admin_version = d.admin_version
WHERE w.is_deleted = false 
  AND d.is_deleted = false 
  AND p.is_deleted = false
```

---

## 📊 **Impact Analysis**

### **Before Admin Version Consistency:**
- **Total joinable records:** 26,536
- **Unique addresses:** 17,718
- **Data inconsistencies:** Temporal mismatches between administrative levels

### **After Admin Version Consistency:**
- **Total joinable records:** 13,354
- **Unique addresses:** 13,354 (0% duplicates)
- **Data quality:** 100% temporally consistent
- **Records removed:** 4,364 inconsistent entries

### **Version Distribution:**
- **Admin Version 1:** 10,033 records (75.13%)
- **Admin Version 2:** 3,321 records (24.87%)

---

## 🎯 **Why This Matters**

### **1. Temporal Consistency**
Administrative boundaries change over time. Without admin_version constraints:
- Ward might join with **old** district data
- District might join with **old** province data
- Results in **geographically impossible** addresses

### **2. Data Integrity**
```sql
-- ❌ WRONG: Can create invalid geographical hierarchies
JOIN mat.district d ON w.district_id = d.district_id

-- ✅ CORRECT: Ensures temporal alignment
JOIN mat.district d ON w.district_id = d.district_id 
    AND d.admin_version = w.admin_version
```

### **3. Business Logic**
- **Administrative reforms** happen periodically (2023, 2024, 2025...)
- **Boundary changes** must be tracked consistently
- **Address standardization** requires accurate hierarchy

---

## 📝 **Implementation Checklist**

### **Files Updated:**
- ✅ `app/ai/db_connector.py` - load_hierarchical_corpus()
- ✅ `app/ai/populate_clean_corpus.py` - administrative data population
- ✅ `docs/02-database/prq_address_clean_corpus.sql` - sample queries
- ✅ `app/api/server.py` - already had admin_version joins

### **Database Operations:**
- ✅ **Truncated** prq.address_clean_corpus table
- ✅ **Repopulated** with 13,354 consistent records
- ✅ **Verified** 100% data consistency
- ✅ **Reset** ID sequence

---

## 🔍 **Validation Queries**

### **Check Admin Version Distribution:**
```sql
SELECT 
    admin_version,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM prq.address_clean_corpus
GROUP BY admin_version
ORDER BY admin_version;
```

### **Verify Join Consistency:**
```sql
-- This should return 0 inconsistent records
SELECT COUNT(*) as inconsistent_records
FROM mat.ward w
LEFT JOIN mat.district d ON w.district_id = d.district_id 
    AND d.admin_version = w.admin_version
LEFT JOIN mat.province p ON d.province_id = p.province_id 
    AND p.admin_version = d.admin_version
WHERE w.is_deleted = false 
  AND (d.district_id IS NULL OR p.province_id IS NULL);
```

### **Corpus Coverage Check:**
```sql
SELECT 
    (SELECT COUNT(*) FROM prq.address_clean_corpus) as corpus_records,
    (SELECT COUNT(*) FROM mat.ward WHERE is_deleted = false) as total_wards,
    ROUND(
        (SELECT COUNT(*) FROM prq.address_clean_corpus) * 100.0 / 
        (SELECT COUNT(*) FROM mat.ward WHERE is_deleted = false), 1
    ) as coverage_percentage;
```

---

## ⚠️ **Common Mistakes to Avoid**

### **❌ Wrong Patterns:**
```sql
-- Missing admin_version in district join
JOIN mat.district d ON w.district_id = d.district_id
JOIN mat.province p ON d.province_id = p.province_id 
    AND p.admin_version = d.admin_version

-- Inconsistent admin_version references  
JOIN mat.district d ON w.district_id = d.district_id 
    AND d.admin_version = 1  -- Hard-coded version
JOIN mat.province p ON d.province_id = p.province_id 
    AND p.admin_version = w.admin_version  -- Different reference
```

### **✅ Correct Pattern:**
```sql
FROM mat.ward w
JOIN mat.district d ON w.district_id = d.district_id 
    AND d.admin_version = w.admin_version
JOIN mat.province p ON d.province_id = p.province_id 
    AND p.admin_version = d.admin_version
```

---

## 🚀 **Performance Considerations**

### **Indexes Required:**
```sql
-- Ensure these indexes exist for optimal performance
CREATE INDEX IF NOT EXISTS idx_ward_district_admin_version 
ON mat.ward (district_id, admin_version);

CREATE INDEX IF NOT EXISTS idx_district_province_admin_version 
ON mat.district (province_id, admin_version);

CREATE INDEX IF NOT EXISTS idx_province_admin_version 
ON mat.province (admin_version);
```

### **Query Performance:**
- **With admin_version:** ~2-3s for full corpus generation
- **Index usage:** High selectivity on compound keys
- **Memory usage:** Consistent and predictable

---

## 📋 **Compliance Verification**

### **Code Review Checklist:**
- [ ] All mat.ward joins include `AND d.admin_version = w.admin_version`
- [ ] All mat.district joins include `AND p.admin_version = d.admin_version`
- [ ] No hard-coded admin_version values (use dynamic references)
- [ ] Proper error handling for missing admin_version data
- [ ] Performance indexes on admin_version columns

### **Testing Requirements:**
- [ ] Unit tests for join consistency
- [ ] Integration tests with different admin_version scenarios
- [ ] Performance tests with full dataset
- [ ] Data validation tests for temporal consistency

---

## 🔄 **Migration History**

| Date | Action | Records | Impact |
|------|--------|---------|--------|
| 2026-05-05 | Initial population | 17,718 | Without admin_version consistency |
| 2026-05-05 | Truncate & repopulate | 13,354 | With admin_version consistency |
| Future | Periodic refresh | TBD | Maintain consistency |

---

## 🔧 **Advanced Features (2026-05-05 Update)**

### **Type Name Cleanup**
Automatically removes administrative type prefixes for cleaner addresses:
```sql
-- Ward names: "Phường Thanh Lương" → "Thanh Lương"
REGEXP_REPLACE(w.ward_name, '^(Phường|Xã|Thị trấn)\\s+', '', 'g')

-- District names: "Quận Hai Bà Trưng" → "Hai Bà Trưng"  
REGEXP_REPLACE(d.district_name, '^(Quận|Huyện|Thành phố|Thị xã)\\s+', '', 'g')

-- Province names: "Thành phố Hà Nội" → "Hà Nội"
REGEXP_REPLACE(p.province_name, '^(Thành phố|Tỉnh)\\s+', '', 'g')
```

### **Admin Version-Specific Address Format**
```sql
-- Admin Version 1: 3-part format
"Thanh Lương, Hai Bà Trưng, Hà Nội"

-- Admin Version 2: 2-part format (district omitted)
"Thanh Lương, Hà Nội"
```

### **Structured Address Components**
```jsonb
-- Admin Version 1
{
  "level_3": "Thanh Lương",
  "level_2": "Hai Bà Trưng", 
  "level_1": "Hà Nội",
  "admin_version": 1,
  "address_type": "administrative_hierarchy"
}

-- Admin Version 2  
{
  "level_3": "Thanh Lương",
  "level_1": "Hà Nội",
  "admin_version": 2,
  "address_type": "administrative_hierarchy"
}
```

### **Current Corpus Statistics**
- **Total Records:** 13,354
- **Admin Version 1:** 10,033 records (3-part addresses)
- **Admin Version 2:** 3,321 records (2-part addresses)
- **Type Name Cleanup:** 100% applied
- **Address Components:** 100% structured

---

**Status:** ✅ **IMPLEMENTED & ENHANCED**  
**Last Update:** 2026-05-05 - Added type cleanup & version-specific formatting  
**Next Review:** When administrative reforms occur  
**Owner:** AI Team  
**Priority:** CRITICAL - Must be followed in ALL mat schema queries