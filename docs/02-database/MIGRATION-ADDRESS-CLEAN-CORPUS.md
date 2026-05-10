# 🔄 Migration Guide: prq.address_clean_corpus

**Ngày tạo:** 2026-05-05  
**Phiên bản:** 1.0  
**Mục tiêu:** Thiết lập bảng corpus địa chỉ chuẩn cho Siamese Retrieval Models

## 📋 Tổng quan Migration

Bảng `prq.address_clean_corpus` được thiết kế để thay thế việc loading corpus từ nhiều nguồn khác nhau, tập trung hóa và tối ưu hóa cho pipeline huấn luyện. Sau **cleanse hàng loạt trên queue**, nên làm đầy lại corpus (ví dụ `QUEUE_STANDARDIZED`) theo [11-OPERATING-PHASES-ABCD.md](../01-ai-training/11-OPERATING-PHASES-ABCD.md) (mục vòng lặp sau release).

**🔥 CRITICAL:** Tất cả joins với mat schema PHẢI include admin_version để đảm bảo temporal consistency:
```sql
FROM mat.ward w
JOIN mat.district d ON w.district_id = d.district_id 
    AND d.admin_version = w.admin_version
JOIN mat.province p ON d.province_id = p.province_id 
    AND p.admin_version = d.admin_version
```

### Lợi ích chính:
- **Tập trung hóa corpus** từ nhiều nguồn (Administrative + Queue + Manual)
- **Temporal-aware matching** với epoch/version support
- **Pre-computed embeddings** cho performance
- **Quality scoring** để filter corpus entries
- **Usage statistics** để optimize corpus

## 🔧 Các bước Migration

### Bước 1: Tạo bảng và indexes

```bash
# Chạy SQL DDL script
psql -h <host> -U <user> -d <database> -f docs/02-database/prq_address_clean_corpus.sql
```

### Bước 2: Populate dữ liệu ban đầu

```bash
# Populate từ Administrative Master Data
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --source administrative --epoch 2025

# Populate từ Queue Standardized Results
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --source queue --min-confidence 0.7

# Hoặc populate tất cả sources
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --source both
```

### Bước 3: Compute embeddings (optional)

```bash
# Compute mGTE embeddings
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --compute-embeddings --embedding-model mgte

# Compute PhoBERT embeddings 
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --compute-embeddings --embedding-model phobert
```

### Bước 4: Kiểm tra integration

```bash
# Test toàn bộ integration
python app/ai/test_clean_corpus.py --config app/ai/config.yaml

# Test nhanh (skip models)
python app/ai/test_clean_corpus.py --config app/ai/config.yaml --skip-models
```

### Bước 5: Monitoring và maintenance

```bash
# Kiểm tra corpus stats
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --stats-only
```

## 📊 Schema Details

### Bảng chính: `prq.address_clean_corpus`

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigserial | Primary key |
| `standardized_address` | text | Địa chỉ chuẩn đầy đủ |
| `source_type` | varchar(20) | 'ADMINISTRATIVE', 'QUEUE_STANDARDIZED', 'MANUAL_CURATED' |
| `quality_score` | numeric(5,4) | Điểm chất lượng [0-1] |
| `admin_epoch` | varchar(10) | Kỳ cải cách hành chính ('2025', '2026'...) |
| `phobert_embedding` | vector(768) | Pre-computed PhoBERT embedding |
| `mgte_embedding` | vector(768) | Pre-computed mGTE embedding |
| `usage_count` | bigint | Số lần được retrieve |

### Key Indexes

- `idx_corpus_active_epoch`: Performance cho active corpus lookup
- `idx_corpus_quality_score`: Sort theo quality score
- `idx_corpus_standardized_address_gin`: Full-text search
- Vector indexes cho similarity search (cần pgvector extension)

## 🔗 Code Integration Points

### 1. DatabaseConnector Methods

```python
# Basic corpus loading
corpus = db.load_clean_corpus(
    admin_epoch="2025",
    source_types=["ADMINISTRATIVE", "QUEUE_STANDARDIZED"], 
    min_quality_score=0.7,
    limit=10000
)

# Loading với metadata (cho temporal-aware)
addresses, metadata = db.load_clean_corpus_with_metadata(
    admin_epoch="2025",
    min_quality_score=0.6
)
```

### 2. Production Pipeline

```python
# production_pipeline.py - Updated to use clean corpus
retriever = SiameseMGTE(model_name=config["model_name"])
corpus_addresses, corpus_metadata = db.load_clean_corpus_with_metadata(...)
retriever.encode_corpus_with_metadata(corpus_addresses, corpus_metadata)
```

### 3. Experiment Runner

```python
# experiment_runner.py - Fallback hierarchy
try:
    corpus = db.load_clean_corpus(...)  # Try clean corpus first
except Exception:
    corpus = db.load_standard_addresses(...)  # Fallback to old method
```

### 4. API Server

```python
# server.py - _load_parser_corpus() updated with clean corpus priority
def _load_parser_corpus(db: Session) -> List[str]:
    # 1. Try prq.address_clean_corpus
    # 2. Fallback to address_cleansing_queue.address_standardized  
    # 3. Final fallback to administrative hierarchy
```

## 🔄 Migration Flow Comparison

### Before (Legacy)

```
Corpus Sources:
├── production_pipeline.py → db.load_hierarchical_corpus() 
├── experiment_runner.py → db.load_standard_addresses()
├── server.py → AddressCleansingQueue.address_standardized
└── Different sources, inconsistent data
```

### After (Clean Corpus)

```  
Centralized Corpus:
└── prq.address_clean_corpus
    ├── ADMINISTRATIVE (từ mat.ward/district/province)
    ├── QUEUE_STANDARDIZED (từ AI processing results) 
    ├── MANUAL_CURATED (thủ công chất lượng cao)
    └── Unified access với quality filtering
```

## ⚡ Performance Expectations

### Corpus Loading

| Method | Before | After | Improvement |
|--------|--------|--------|-------------|
| Load 10K addresses | ~2-3s | ~0.5-1s | 2-3x faster |
| Memory usage | Variable | Optimized | ~30% reduction |
| Query consistency | Medium | High | Standardized |

### Embedding Performance 

- **Pre-computed embeddings**: Loại bỏ encoding overhead tại runtime
- **Vector indexes**: Fast similarity search với pgvector
- **Quality filtering**: Chỉ load corpus entries chất lượng cao

## 🛠️ Troubleshooting

### Issue 1: Empty corpus

```bash
# Check if table exists and has data
psql -c "SELECT COUNT(*), source_type FROM prq.address_clean_corpus GROUP BY source_type;"

# Re-populate if needed
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --source both
```

### Issue 2: Model loading errors

```bash
# Test without models first
python app/ai/test_clean_corpus.py --config app/ai/config.yaml --skip-models

# Check embedding dependencies
pip install sentence-transformers torch
```

### Issue 3: Performance issues

```sql
-- Check index usage
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM prq.address_clean_corpus 
WHERE is_active = true AND admin_epoch = '2025' 
ORDER BY quality_score DESC LIMIT 1000;

-- Recreate indexes if needed
REINDEX TABLE prq.address_clean_corpus;
```

## 📈 Monitoring & Maintenance

### Daily monitoring queries

```sql
-- Corpus growth tracking
SELECT 
    source_type,
    admin_epoch,
    COUNT(*) as total,
    COUNT(CASE WHEN mgte_embedding IS NOT NULL THEN 1 END) as with_embeddings,
    AVG(quality_score) as avg_quality
FROM prq.address_clean_corpus 
WHERE is_active = true
GROUP BY source_type, admin_epoch;

-- Usage statistics
SELECT 
    percentile_cont(0.5) WITHIN GROUP (ORDER BY usage_count) as median_usage,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY usage_count) as p95_usage,
    MAX(last_used_at) as last_activity
FROM prq.address_clean_corpus
WHERE is_active = true;
```

### Weekly maintenance tasks

```bash
# Update usage statistics và cleanup unused entries
# (Script này sẽ được phát triển trong future iterations)

# Re-compute embeddings for updated entries
python app/ai/populate_clean_corpus.py --config app/ai/config.yaml --compute-embeddings --embedding-model mgte
```

## 🎯 Next Steps

1. **Monitoring dashboard** cho corpus quality và usage
2. **Auto-refresh mechanism** để sync với queue updates  
3. **A/B testing framework** cho different corpus strategies
4. **Advanced filtering** theo geographic regions
5. **Corpus deduplication** algorithms

---

**Liên hệ:** AI Team  
**Documentation version:** 1.0  
**Last updated:** 2026-05-05