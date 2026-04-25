```sql
CREATE TABLE prq.address_cleansing_queue (
	id bigserial NOT NULL,
	source_system varchar(50) NULL, -- Ví dụ: 'SHOPEE', 'CRM_INTERNAL'
	
    -- 1. RAW DATA (Input)
    address_raw text NOT NULL,
	order_count int8 DEFAULT 1, 

    -- 2. PROCESSING STATE
	processing_status varchar(30) DEFAULT 'PENDING' NOT NULL, 
	processing_method varchar(30) NULL, -- Cập nhật: 'SQL_RULE', 'ENSEMBLE_AI', 'MANUAL'
    error_message text NULL, 

    -- 3. ADMINISTRATIVE DATA (Level 1, 2, 3)
	province_id int4 NULL,
	province_name text NULL,
	district_id int4 NULL,
	district_name text NULL,
	ward_id int4 NULL,
	ward_name text NULL,
	
    -- 4. CORE ADDRESS (AI Outputs - A/B Testing)
    street_address text NULL, 
    
    -- Kết quả từ PhoBERT
	phobert_parsed_components jsonb NULL, -- Lưu JSON của PhoBERT: {"bld": "...", "str": "..."}
	phobert_confidence_score numeric(5, 4) NULL,
    
    -- Kết quả từ MGTE
	mgte_parsed_components jsonb NULL, -- Lưu JSON của MGTE: {"bld": "...", "str": "..."}
	mgte_confidence_score numeric(5, 4) NULL,
    
    -- 5. DECISION & STANDARDIZED RESULT
    selected_ai_model varchar(20) NULL, -- Lưu 'PHOBERT' hoặc 'MGTE' làm cơ sở quyết định
    address_standardized text NULL, -- Chuỗi địa chỉ đẹp cuối cùng được tạo ra từ model chiến thắng
	postal_code varchar(20) NULL,
	country_code bpchar(2) DEFAULT 'VN'::bpchar NULL,
	latitude numeric(10, 7) NULL,
	longitude numeric(10, 7) NULL,

    -- 6. EMBEDDINGS
	phobert_embedding jsonb NULL, 
	mgte_embedding jsonb NULL,
	
    created_at timestamp DEFAULT now() NOT NULL,
    updated_at timestamp DEFAULT now() NOT NULL,

    -- ĐÃ SỬA: Tên constraint phải là duy nhất
	CONSTRAINT check_phobert_confidence CHECK (((phobert_confidence_score >= (0)::numeric) AND (phobert_confidence_score <= (1)::numeric))),
	CONSTRAINT check_mgte_confidence CHECK (((mgte_confidence_score >= (0)::numeric) AND (mgte_confidence_score <= (1)::numeric))),
	CONSTRAINT address_cleansing_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_address_status ON prq.address_cleansing_queue (processing_status);
```

```sql
-- 1. Mô tả cho toàn bộ bảng
COMMENT ON TABLE prq.address_cleansing_queue IS 'Hàng đợi xử lý và chuẩn hóa địa chỉ (Hỗ trợ A/B Testing PhoBERT vs MGTE)';

-- 2. Mô tả cho từng cột
COMMENT ON COLUMN prq.address_cleansing_queue.source_system IS 'Hệ thống nguồn đẩy dữ liệu vào (Ví dụ: SHOPEE, CRM_INTERNAL, TIKI)';

COMMENT ON COLUMN prq.address_cleansing_queue.address_raw IS 'RAW DATA: Dữ liệu địa chỉ thô nguyên bản do khách hàng nhập';
COMMENT ON COLUMN prq.address_cleansing_queue.order_count IS 'RAW DATA: Số lượng đơn hàng/lần xuất hiện của địa chỉ này (dùng để ưu tiên xử lý các địa chỉ lặp lại nhiều)';

COMMENT ON COLUMN prq.address_cleansing_queue.processing_status IS 'STATE: Trạng thái xử lý của luồng dữ liệu (PENDING, PROCESSING, COMPLETED, FAILED)';
COMMENT ON COLUMN prq.address_cleansing_queue.processing_method IS 'STATE: Phương pháp đã được áp dụng để xử lý (SQL_RULE, ENSEMBLE_AI, MANUAL)';
COMMENT ON COLUMN prq.address_cleansing_queue.error_message IS 'STATE: Ghi nhận nguyên nhân lỗi chi tiết nếu batch bị crash hoặc chạy thất bại';

COMMENT ON COLUMN prq.address_cleansing_queue.province_id IS 'ADMIN DATA: ID Tỉnh/Thành phố (Map với master_province)';
COMMENT ON COLUMN prq.address_cleansing_queue.district_id IS 'ADMIN DATA: ID Quận/Huyện (Map với master_district)';
COMMENT ON COLUMN prq.address_cleansing_queue.ward_id IS 'ADMIN DATA: ID Phường/Xã (Map với master_ward)';

COMMENT ON COLUMN prq.address_cleansing_queue.street_address IS 'CORE ADDRESS: Phần lõi địa chỉ (address_line) được bóc tách bằng SQL Rule, dùng làm input cho các mô hình AI';

COMMENT ON COLUMN prq.address_cleansing_queue.phobert_parsed_components IS 'AI RESULT: Kết quả bóc tách thực thể (NER) từ PhoBERT (Format: JSONB)';
COMMENT ON COLUMN prq.address_cleansing_queue.phobert_confidence_score IS 'AI RESULT: Độ tự tin dự đoán của mô hình PhoBERT (0.0000 -> 1.0000)';

COMMENT ON COLUMN prq.address_cleansing_queue.mgte_parsed_components IS 'AI RESULT: Kết quả bóc tách thực thể (NER) từ MGTE (Format: JSONB)';
COMMENT ON COLUMN prq.address_cleansing_queue.mgte_confidence_score IS 'AI RESULT: Độ tự tin dự đoán của mô hình MGTE (0.0000 -> 1.0000)';

COMMENT ON COLUMN prq.address_cleansing_queue.selected_ai_model IS 'DECISION: Ghi nhận AI nào (PHOBERT hoặc MGTE) đã chiến thắng dựa trên logic so sánh confidence score';
COMMENT ON COLUMN prq.address_cleansing_queue.address_standardized IS 'DECISION: Chuỗi địa chỉ hoàn hảo cuối cùng được ghép lại từ kết quả NER của mô hình chiến thắng';

COMMENT ON COLUMN prq.address_cleansing_queue.phobert_embedding IS 'EMBEDDING: Vector nhúng sinh ra từ PhoBERT, dùng để so sánh độ tương đồng (Deduplication)';
COMMENT ON COLUMN prq.address_cleansing_queue.mgte_embedding IS 'EMBEDDING: Vector nhúng sinh ra từ MGTE';
```