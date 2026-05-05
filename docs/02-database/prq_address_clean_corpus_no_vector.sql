-- ============================================================================
-- Table: prq.address_clean_corpus (WITHOUT vector columns)
-- Purpose: Corpus địa chỉ chuẩn cho Siamese Retrieval Models (Phase 3)
-- Created: 2026-05-05
-- Version: 1.0 (No pgvector dependency)
-- ============================================================================

CREATE TABLE prq.address_clean_corpus (
    id bigserial NOT NULL,
    
    -- 1. CORE ADDRESS DATA
    standardized_address text NOT NULL, -- Địa chỉ chuẩn đầy đủ để làm corpus
    address_components jsonb NULL, -- Structured components: {"street_number": "123", "route": "Đường ABC", ...}
    
    -- 2. SOURCE & METADATA
    source_type varchar(20) NOT NULL, -- 'ADMINISTRATIVE', 'QUEUE_STANDARDIZED', 'MANUAL_CURATED'
    source_id bigint NULL, -- Reference đến record gốc (queue.id, ward.id, etc.)
    quality_score numeric(5, 4) DEFAULT 1.0000, -- Điểm chất lượng corpus [0-1]
    
    -- 3. ADMINISTRATIVE HIERARCHY (for context)
    province_id int4 NULL,
    province_name text NULL,
    district_id int4 NULL, 
    district_name text NULL,
    ward_id int4 NULL,
    ward_name text NULL,
    
    -- 4. TEMPORAL & VERSIONING (support epoch filtering)
    admin_epoch varchar(10) DEFAULT '2025' NOT NULL, -- Kỳ cải cách hành chính
    admin_version int4 DEFAULT 1 NOT NULL, -- Version của dữ liệu hành chính
    effective_date date DEFAULT CURRENT_DATE,
    
    -- 5. PRE-COMPUTED EMBEDDINGS (JSON format instead of vector)
    phobert_embedding jsonb NULL, -- PhoBERT embedding as JSON array
    mgte_embedding jsonb NULL, -- mGTE embedding as JSON array
    embedding_version varchar(10) DEFAULT 'v1' NOT NULL, -- Track embedding model version
    
    -- 6. USAGE STATISTICS
    usage_count int8 DEFAULT 0, -- Số lần địa chỉ này được retrieve
    last_used_at timestamp NULL, -- Lần cuối được sử dụng
    
    -- 7. AUDIT & LIFECYCLE
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    updated_at timestamp DEFAULT now() NOT NULL,
    created_by varchar(50) DEFAULT 'SYSTEM' NOT NULL,
    
    -- CONSTRAINTS
    CONSTRAINT address_clean_corpus_pkey PRIMARY KEY (id),
    CONSTRAINT check_quality_score CHECK ((quality_score >= 0.0000 AND quality_score <= 1.0000)),
    CONSTRAINT check_source_type CHECK (source_type IN ('ADMINISTRATIVE', 'QUEUE_STANDARDIZED', 'MANUAL_CURATED')),
    CONSTRAINT check_admin_epoch CHECK (admin_epoch IN ('2023', '2024', '2025', '2026')),
    CONSTRAINT unique_standardized_address_epoch UNIQUE (standardized_address, admin_epoch, source_type)
);

-- ============================================================================
-- INDEXES - Optimized for Siamese Retrieval Performance
-- ============================================================================

-- 1. Primary lookup indexes
CREATE INDEX idx_corpus_active_epoch ON prq.address_clean_corpus (is_active, admin_epoch) WHERE is_active = true;
CREATE INDEX idx_corpus_source_type ON prq.address_clean_corpus (source_type, is_active);
CREATE INDEX idx_corpus_quality_score ON prq.address_clean_corpus (quality_score DESC) WHERE is_active = true;

-- 2. Administrative hierarchy indexes
CREATE INDEX idx_corpus_province ON prq.address_clean_corpus (province_id) WHERE is_active = true;
CREATE INDEX idx_corpus_district ON prq.address_clean_corpus (district_id) WHERE is_active = true; 
CREATE INDEX idx_corpus_ward ON prq.address_clean_corpus (ward_id) WHERE is_active = true;

-- 3. Full-text search support
CREATE INDEX idx_corpus_standardized_address_gin ON prq.address_clean_corpus 
    USING gin(to_tsvector('english', standardized_address)) WHERE is_active = true;

-- 4. Performance indexes
CREATE INDEX idx_corpus_usage_stats ON prq.address_clean_corpus (usage_count DESC, last_used_at DESC);
CREATE INDEX idx_corpus_source_ref ON prq.address_clean_corpus (source_type, source_id);

-- ============================================================================
-- TABLE & COLUMN COMMENTS
-- ============================================================================

COMMENT ON TABLE prq.address_clean_corpus IS 'Corpus địa chỉ chuẩn cho Siamese Retrieval Models - Phase 3 Training Pipeline. Hỗ trợ temporal-aware matching và pre-computed embeddings.';

-- Core Address Data
COMMENT ON COLUMN prq.address_clean_corpus.standardized_address IS 'CORE: Địa chỉ chuẩn đầy đủ làm corpus cho similarity search (VD: "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")';
COMMENT ON COLUMN prq.address_clean_corpus.address_components IS 'CORE: Structured components dạng JSON {"street_number": "123", "route": "Đường Lê Lợi", "level_3": "Phường Bến Nghé", ...}';

-- Source & Metadata  
COMMENT ON COLUMN prq.address_clean_corpus.source_type IS 'SOURCE: Nguồn gốc corpus - ADMINISTRATIVE (từ master data), QUEUE_STANDARDIZED (từ AI processing), MANUAL_CURATED (thủ công)';
COMMENT ON COLUMN prq.address_clean_corpus.source_id IS 'SOURCE: Reference ID đến record gốc (prq.address_cleansing_queue.id, mat.ward.id, etc.)';
COMMENT ON COLUMN prq.address_clean_corpus.quality_score IS 'METADATA: Điểm chất lượng corpus [0-1] - dùng để filter trong retrieval';

-- Administrative Hierarchy
COMMENT ON COLUMN prq.address_clean_corpus.province_id IS 'ADMIN: ID Tỉnh/Thành phố (reference mat.province.province_id)';
COMMENT ON COLUMN prq.address_clean_corpus.district_id IS 'ADMIN: ID Quận/Huyện (reference mat.district.district_id)';
COMMENT ON COLUMN prq.address_clean_corpus.ward_id IS 'ADMIN: ID Phường/Xã (reference mat.ward.ward_id)';

-- Temporal & Versioning
COMMENT ON COLUMN prq.address_clean_corpus.admin_epoch IS 'TEMPORAL: Kỳ cải cách hành chính (2025, 2026...) - support epoch-based filtering';
COMMENT ON COLUMN prq.address_clean_corpus.admin_version IS 'TEMPORAL: Version của administrative data - track changes over time';
COMMENT ON COLUMN prq.address_clean_corpus.effective_date IS 'TEMPORAL: Ngày có hiệu lực của record corpus này';

-- Pre-computed Embeddings (JSON format)
COMMENT ON COLUMN prq.address_clean_corpus.phobert_embedding IS 'EMBEDDING: Vector nhúng từ PhoBERT model stored as JSON array - pre-computed cho performance';
COMMENT ON COLUMN prq.address_clean_corpus.mgte_embedding IS 'EMBEDDING: Vector nhúng từ mGTE model stored as JSON array - pre-computed cho performance';
COMMENT ON COLUMN prq.address_clean_corpus.embedding_version IS 'EMBEDDING: Track version của embedding models (v1, v2...) để handle model updates';

-- Usage Statistics
COMMENT ON COLUMN prq.address_clean_corpus.usage_count IS 'STATS: Số lần corpus entry này được retrieve - track popularity';
COMMENT ON COLUMN prq.address_clean_corpus.last_used_at IS 'STATS: Timestamp lần cuối được sử dụng - maintenance & cleanup';

-- Lifecycle
COMMENT ON COLUMN prq.address_clean_corpus.is_active IS 'LIFECYCLE: Status active/inactive - soft delete support';
COMMENT ON COLUMN prq.address_clean_corpus.created_by IS 'AUDIT: User/system tạo record (SYSTEM, USERNAME, etc.)';

-- ============================================================================
-- TRIGGERS - Auto-update timestamps
-- ============================================================================

CREATE OR REPLACE FUNCTION update_address_clean_corpus_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_address_clean_corpus_updated_at
    BEFORE UPDATE ON prq.address_clean_corpus
    FOR EACH ROW EXECUTE FUNCTION update_address_clean_corpus_updated_at();