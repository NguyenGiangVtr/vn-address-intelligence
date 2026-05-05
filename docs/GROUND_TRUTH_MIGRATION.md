# Ground Truth Migration Guide

## Tổng quan

Document này hướng dẫn việc di chuyển bảng `mat.google_ground_truth` sang schema `prq` với tên mới `prq.ground_truth` để sử dụng linh hoạt hơn trong training và parser.

## Lý do di chuyển

1. **Schema phù hợp hơn**: `prq` (Processing Queue) phù hợp cho việc xử lý dữ liệu hơn `mat` (Master Data)
2. **Tính năng mở rộng**: Thêm các metadata như quality score, validation status
3. **Hiệu suất tốt hơn**: Index tối ưu cho query performance
4. **Sử dụng thống nhất**: Interface chung cho training và parser

## Cấu trúc mới

### Bảng `prq.ground_truth`

```sql
-- Bảng ground truth mới với các tính năng mở rộng
CREATE TABLE prq.ground_truth (
    id BIGINT PRIMARY KEY,
    address TEXT NOT NULL,
    old_address TEXT,
    
    -- Current administrative IDs (after mapping)
    ward_id INTEGER,
    district_id INTEGER, 
    province_id INTEGER,
    
    -- Original IDs from Typesense/old database
    old_ward_id INTEGER,
    old_district_id INTEGER,
    old_province_id INTEGER,
    
    -- Multilingual support
    old_address_eng TEXT,
    address_eng TEXT,
    
    -- Geolocation
    latitude FLOAT,
    longitude FLOAT,
    
    -- Popularity/usage metrics
    popular INTEGER DEFAULT 0,
    
    -- Processing metadata (MỚI)
    source_system VARCHAR(50) DEFAULT 'TYPESENSE',  -- TYPESENSE, GOOGLE, MANUAL
    data_quality_score FLOAT,                       -- 0-1 score for data quality
    is_validated BOOLEAN DEFAULT FALSE,              -- Human validation status
    validation_notes TEXT,                          -- Notes from validation
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes để tối ưu performance
CREATE INDEX idx_ground_truth_province ON prq.ground_truth(province_id);
CREATE INDEX idx_ground_truth_district ON prq.ground_truth(district_id);
CREATE INDEX idx_ground_truth_ward ON prq.ground_truth(ward_id);
CREATE INDEX idx_ground_truth_location ON prq.ground_truth(latitude, longitude);
```

### Bảng `mat.admin_unit_mapping` (Mới)

```sql
-- Bảng ánh xạ ID từ database cũ sang database mới
CREATE TABLE mat.admin_unit_mapping (
    id SERIAL PRIMARY KEY,
    level INTEGER NOT NULL,        -- 1=province, 2=district, 3=ward
    old_id INTEGER NOT NULL,       -- ID trong database cũ
    new_id INTEGER NOT NULL,       -- ID trong database mới
    admin_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Hướng dẫn Migration

### 1. Chạy Migration Script

```bash
# Kiểm tra dữ liệu trước khi migrate
python scripts/migration/migrate_ground_truth_to_prq.py --validate-only

# Thực hiện migration
python scripts/migration/migrate_ground_truth_to_prq.py --migrate

# Xóa bảng cũ sau khi migrate thành công (tùy chọn)
python scripts/migration/migrate_ground_truth_to_prq.py --migrate --drop-old-table
```

### 2. Test Migration

```bash
# Test toàn bộ functionality
python scripts/test_ground_truth_service.py --test-all

# Test từng phần
python scripts/test_ground_truth_service.py --test-basic
python scripts/test_ground_truth_service.py --test-corpus
python scripts/test_ground_truth_service.py --test-performance
```

## Sử dụng Ground Truth Service

### 1. Import Service

```python
from app.services.ground_truth_service import (
    get_ground_truth_service, 
    get_corpus_for_training, 
    get_training_data
)
```

### 2. Lấy Corpus cho Training

```python
# Cách đơn giản
corpus = get_corpus_for_training(limit=10000)

# Cách chi tiết với filter
with get_ground_truth_service() as service:
    corpus = service.get_corpus_addresses(
        limit=10000,
        min_quality_score=0.7,
        source_systems=['TYPESENSE', 'GOOGLE']
    )
```

### 3. Lấy Training Data

```python
# Lấy DataFrame cho training
training_df = get_training_data(limit=1000)

# Lấy training pairs
with get_ground_truth_service() as service:
    pairs = service.get_training_pairs(limit=1000)
    # pairs = [(raw_address, normalized_address), ...]
```

### 4. Filter theo Administrative Units

```python
with get_ground_truth_service() as service:
    # Lấy data theo tỉnh/thành
    hcm_data = service.get_validated_addresses(
        province_id=79,  # TP.HCM
        limit=1000,
        validate_admin_units=True
    )
    
    # Lấy data đã được validate
    validated_data = service.get_validated_addresses(
        include_unvalidated=False,
        min_quality_score=0.8
    )
```

### 5. Statistics và Monitoring

```python
with get_ground_truth_service() as service:
    stats = service.get_statistics()
    print(f"Total records: {stats['total_records']}")
    print(f"Validation rate: {stats['validation_rate']:.2%}")
    print(f"Average quality: {stats['quality_scores']['average']:.3f}")
```

## Cập nhật Configuration

### 1. Experiment Config

Sử dụng config mới `app/ai/config_ground_truth.yaml`:

```yaml
experiment:
  use_ground_truth_service: true
  ground_truth_config:
    min_quality_score: 0.7
    source_systems: ["TYPESENSE", "GOOGLE"]
    include_unvalidated: false
    validate_admin_units: true
```

### 2. Parser Config

Parser sẽ tự động sử dụng Ground Truth Service với fallback hierarchy:
1. `prq.ground_truth` (Ground Truth Service)
2. `prq.address_clean_corpus` 
3. `prq.address_cleansing_queue.address_standardized`
4. Administrative hierarchy

## Validation Query

Query để validate migration thành công:

```sql
-- So sánh số lượng records
SELECT 
    'mat.google_ground_truth' as table_name,
    COUNT(*) as record_count
FROM mat.google_ground_truth
UNION ALL
SELECT 
    'prq.ground_truth' as table_name,
    COUNT(*) as record_count  
FROM prq.ground_truth;

-- Kiểm tra sample data
SELECT 
    gt.id,
    gt.address,
    gt.source_system,
    gt.is_validated,
    w.ward_name,
    d.district_name,
    p.province_name
FROM prq.ground_truth gt
JOIN mat.ward w ON gt.ward_id = w.old_id AND w.is_deleted = false AND w.is_active = true
JOIN mat.district d ON gt.district_id = d.old_id AND d.is_deleted = false AND d.is_active = true  
JOIN mat.province p ON d.province_id = p.old_id AND p.is_deleted = false
LIMIT 10;
```

## Troubleshooting

### 1. Migration Issues

```bash
# Nếu migration fails, check logs
python scripts/migration/migrate_ground_truth_to_prq.py --validate-only

# Clear target table và retry
python scripts/migration/migrate_ground_truth_to_prq.py --migrate
```

### 2. Performance Issues

```bash
# Kiểm tra indexes
python scripts/test_ground_truth_service.py --test-performance

# Nếu chậm, có thể cần tạo thêm indexes:
# CREATE INDEX idx_ground_truth_quality ON prq.ground_truth(data_quality_score) WHERE data_quality_score IS NOT NULL;
```

### 3. Empty Corpus

Nếu corpus trống, kiểm tra:

1. Data đã được migrate chưa
2. Quality score filter có quá cao không
3. Source system filter có đúng không

```python
# Debug corpus loading
with get_ground_truth_service() as service:
    stats = service.get_statistics()
    print("Statistics:", stats)
    
    # Try with relaxed filters
    corpus = service.get_corpus_addresses(
        limit=100,
        min_quality_score=0.0,  # Lower threshold
        source_systems=None     # All sources
    )
    print("Corpus with relaxed filters:", len(corpus))
```

## Performance Improvements

1. **Indexes**: Đã tạo indexes tối ưu cho các query thường dùng
2. **Quality filtering**: Chỉ lấy data chất lượng cao cho training
3. **Source prioritization**: Ưu tiên data từ Google/Typesense
4. **Caching**: Service có thể cache corpus để tăng tốc

## Next Steps

1. Chạy migration trong production
2. Test performance với full dataset
3. Monitor training quality với corpus mới
4. Cập nhật quality scores dựa trên usage patterns
5. Implement automated validation workflows