# Danh mục bảng / view (PostgreSQL)

File được sinh tự động bởi [`scripts/diagnostics/db_table_catalog.py`](../scripts/diagnostics/db_table_catalog.py).

| Thuộc tính | Giá trị |
|---|---|
| Thời điểm xuất | 2026-05-12 01:13:49 UTC |
| `DB_NAME` | `vn_address_intelligence_db` |
| Số đối tượng | 32 |

**Phiên bản PostgreSQL**

PostgreSQL 12.22 (Ubuntu 12.22-0ubuntu0.20.04.4) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 9.4.0-1ubuntu1~20.04.2) 9.4.0, 64-bit

## Tóm tắt theo schema

- **`ai`** (1): `ai.prelabeler_testcases`
- **`ath`** (9): `ath.benchmark_dataset`, `ath.benchmark_model_baselines`, `ath.benchmark_run_result`, `ath.email_verifications`, `ath.prelabeler_settings`, `ath.sync_log`, `ath.training_datasets`, `ath.training_history`, `ath.typesense_ground_truth_sync_run`
- **`mat`** (9): `mat.area_polygon`, `mat.district`, `mat.district_old`, `mat.province`, `mat.province_old`, `mat.unit_edge`, `mat.ward`, `mat.ward_mapping`, `mat.ward_old`
- **`osm`** (4): `osm.buildings`, `osm.pois`, `osm.raw_entities`, `osm.streets`
- **`prq`** (8): `prq.address_clean_corpus`, `prq.address_cleansing_queue`, `prq.address_cleansing_queue_backup_20260506_014244`, `prq.address_cleansing_queue_backup_20260510_072057`, `prq.address_cleansing_queue_backup_20260510_072119`, `prq.ground_truth`, `prq.raw_addresses`, `prq.v_ground_truth_admin`
- **`public`** (1): `public.auth_users`

## Schema `ai`

### `ai.prelabeler_testcases`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`text`)
- `name` (`text`)
- `input` (`jsonb`)
- `expected` (`jsonb`)
- `strict` (`boolean`)
- `created_at` (`timestamp with time zone`)
- `updated_at` (`timestamp with time zone`)
- `test_result` (`jsonb`)
- `tested_at` (`timestamp with time zone`)
- `input_raw_address_norm` (`text`)
- `note` (`text`)
- `predict_meta` (`jsonb`)

*(… còn 1 cột khác.)*

## Schema `ath`

### `ath.benchmark_dataset`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `dataset_code` (`character varying(10)`)
- `raw_address` (`text`)
- `expected_ward_id` (`integer`)
- `expected_district_id` (`integer`)
- `expected_province_id` (`integer`)
- `noise_type` (`character varying(50)`)
- `admin_version` (`integer`)
- `notes` (`text`)
- `created_at` (`timestamp without time zone`)

### `ath.benchmark_model_baselines`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `model_key` (`character varying(32)`)
- `model_name` (`character varying(120)`)
- `f1` (`double precision`)
- `throughput` (`double precision`)
- `cost_per_million` (`double precision`)
- `google_match` (`double precision`)
- `sample_size` (`integer`)
- `notes` (`text`)
- `created_at` (`timestamp without time zone`)
- `updated_at` (`timestamp without time zone`)

### `ath.benchmark_run_result`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `run_id` (`character varying(50)`)
- `dataset_code` (`character varying(10)`)
- `model_key` (`character varying(32)`)
- `sample_id` (`integer`)
- `predicted_ward_id` (`integer`)
- `predicted_district_id` (`integer`)
- `predicted_province_id` (`integer`)
- `acs_score` (`numeric(5,4)`)
- `acs_decision` (`character varying(20)`)
- `address_epoch` (`character varying(20)`)
- `latency_ms` (`double precision`)

*(… còn 2 cột khác.)*

### `ath.email_verifications`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `email` (`character varying(150)`)
- `code` (`character varying(10)`)
- `expires_at` (`timestamp without time zone`)
- `is_verified` (`boolean`)
- `created_at` (`timestamp without time zone`)

### `ath.prelabeler_settings`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `payload` (`json`)
- `updated_at` (`timestamp without time zone`)

### `ath.sync_log`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `sync_source` (`character varying(50)`)
- `level` (`character varying(20)`)
- `unit_id` (`integer`)
- `change_type` (`character varying(30)`)
- `old_value` (`json`)
- `new_value` (`json`)
- `synced_at` (`timestamp without time zone`)
- `records_affected` (`integer`)
- `run_id` (`character varying(50)`)

### `ath.training_datasets`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `raw_text` (`text`)
- `ner_tags_json` (`json`)
- `is_synthetic` (`boolean`)
- `noise_level` (`character varying(20)`)
- `created_at` (`timestamp without time zone`)

### `ath.training_history`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `version` (`character varying(20)`)
- `accuracy` (`double precision`)
- `f1_score` (`double precision`)
- `loss` (`double precision`)
- `samples_count` (`integer`)
- `created_at` (`timestamp without time zone`)
- `notes` (`text`)

### `ath.typesense_ground_truth_sync_run`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `started_at` (`timestamp with time zone`)
- `finished_at` (`timestamp with time zone`)
- `collection` (`text`)
- `records_scanned` (`integer`)
- `records_upserted` (`integer`)
- `filter_province_id` (`integer`)
- `notes` (`text`)

## Schema `mat`

### `mat.area_polygon`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `unit_level` (`character varying(20)`)
- `unit_id` (`integer`)
- `unit_name` (`character varying(200)`)
- `geojson` (`json`)
- `source` (`character varying(50)`)
- `admin_version` (`integer`)
- `created_at` (`timestamp without time zone`)
- `updated_at` (`timestamp without time zone`)

### `mat.district`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `district_id` (`integer`)
- `province_id` (`integer`)
- `district_no` (`character varying(20)`)
- `district_name` (`character varying(150)`)
- `type_name` (`character varying(128)`)
- `location` (`character varying(512)`)
- `is_default` (`boolean`)
- `created_user` (`integer`)
- `created_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `updated_date` (`timestamp without time zone`)
- `is_deleted` (`boolean`)

*(… còn 18 cột khác.)*

### `mat.district_old`

- **Loại:** table

**COMMENT ON TABLE**

Snapshot of gse_sprint.mat.district from host 10.10.13.126, cloned at 2026-05-10T01:11:29 (786 rows). Source: scripts/migration/clone_old_mat_tables.py

**Cột (mẫu / có comment)**

- `province_id` (`integer`)
- `district_no` (`character varying(5)`)
- `district_name` (`character varying(150)`)
- `type_name` (`character varying(128)`)
- `location` (`text`)
- `is_default` (`boolean`)
- `created_user` (`integer`)
- `created_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `updated_date` (`timestamp without time zone`)
- `is_deleted` (`boolean`)
- `district_name_en` (`character varying(200)`)

*(… còn 9 cột khác.)*

### `mat.province`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `province_id` (`integer`)
- `area_id` (`integer`)
- `bonus_area_id` (`integer`)
- `country_id` (`integer`)
- `province_no` (`character varying(20)`)
- `province_name` (`character varying(150)`)
- `type_name` (`character varying(64)`)
- `is_default` (`boolean`)
- `created_user` (`integer`)
- `created_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `updated_date` (`timestamp without time zone`)

*(… còn 25 cột khác.)*

### `mat.province_old`

- **Loại:** table

**COMMENT ON TABLE**

Snapshot of gse_sprint.mat.province from host 10.10.13.126, cloned at 2026-05-10T01:11:28 (97 rows). Source: scripts/migration/clone_old_mat_tables.py

**Cột (mẫu / có comment)**

- `area_id` (`integer`)
- `bonus_area_id` (`integer`)
- `country_id` (`integer`)
- `province_no` (`integer`)
- `province_name` (`character varying(150)`)
- `type_name` (`character varying(64)`)
- `is_default` (`boolean`)
- `created_user` (`integer`)
- `created_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `updated_date` (`timestamp without time zone`)
- `is_deleted` (`boolean`)

*(… còn 18 cột khác.)*

### `mat.unit_edge`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `from_unit_id` (`integer`)
- `from_level` (`character varying(20)`)
- `to_unit_id` (`integer`)
- `to_level` (`character varying(20)`)
- `relationship_type` (`character varying(50)`)
- `effective_date` (`timestamp without time zone`)
- `resolution_ref` (`character varying(200)`)
- `notes` (`text`)
- `created_at` (`timestamp without time zone`)

### `mat.ward`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `ward_id` (`integer`)
- `district_id` (`integer`)
- `ward_no` (`character varying(20)`)
- `ward_name` (`character varying(150)`)
- `type_name` (`character varying(128)`)
- `location` (`character varying(512)`)
- `is_default` (`boolean`)
- `created_user` (`integer`)
- `created_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `updated_date` (`timestamp without time zone`)
- `is_deleted` (`boolean`)

*(… còn 18 cột khác.)*

### `mat.ward_mapping`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `ward_mapping_id` (`integer`)
- `ward_id_old` (`integer`)
- `province_id_old` (`integer`)
- `ward_id_new` (`integer`)
- `province_id_new` (`integer`)
- `effective_date_from` (`date`)
- `effective_date_to` (`date`)
- `created_date` (`timestamp without time zone`)
- `created_user` (`integer`)
- `updated_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `is_deleted` (`boolean`)

*(… còn 5 cột khác.)*

### `mat.ward_old`

- **Loại:** table

**COMMENT ON TABLE**

Snapshot of gse_sprint.mat.ward from host 10.10.13.126, cloned at 2026-05-10T01:11:29 (16,131 rows). Source: scripts/migration/clone_old_mat_tables.py

**Cột (mẫu / có comment)**

- `district_id` (`integer`)
- `ward_no` (`character varying(5)`)
- `ward_name` (`character varying(150)`)
- `type_name` (`character varying(128)`)
- `location` (`text`)
- `is_default` (`boolean`)
- `created_user` (`integer`)
- `created_date` (`timestamp without time zone`)
- `updated_user` (`integer`)
- `updated_date` (`timestamp without time zone`)
- `is_deleted` (`boolean`)
- `ward_name_en` (`character varying(200)`)

*(… còn 8 cột khác.)*

## Schema `osm`

### `osm.buildings`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `name` (`character varying(255)`)
- `type` (`character varying(100)`)
- `created_at` (`timestamp without time zone`)
- `province_id` (`integer`)
- `province_name` (`character varying(150)`)

### `osm.pois`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `name` (`character varying(255)`)
- `type` (`character varying(100)`)
- `created_at` (`timestamp without time zone`)
- `province_id` (`integer`)
- `province_name` (`character varying(150)`)

### `osm.raw_entities`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `osm_type` (`character varying(20)`)
- `tags` (`json`)
- `created_at` (`timestamp without time zone`)
- `province_id` (`integer`)
- `province_name` (`character varying(150)`)

### `osm.streets`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `name` (`character varying(255)`)
- `province_id` (`integer`)
- `created_at` (`timestamp without time zone`)
- `province_name` (`character varying(150)`)

## Schema `prq`

### `prq.address_clean_corpus`

- **Loại:** table

**COMMENT ON TABLE**

Corpus địa chỉ chuẩn cho Siamese Retrieval Models - Phase 3 Training Pipeline. Hỗ trợ temporal-aware matching và pre-computed embeddings.

**Cột (mẫu / có comment)**

- `standardized_address` (`text`) — CORE: Địa chỉ chuẩn đầy đủ làm corpus cho similarity search (VD: "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")
- `address_components` (`jsonb`) — CORE: Structured components dạng JSON {"street_number": "123", "route": "Đường Lê Lợi", "level_3": "Phường Bến Nghé", ...}
- `source_type` (`character varying(20)`) — SOURCE: Nguồn gốc corpus - ADMINISTRATIVE (từ master data), QUEUE_STANDARDIZED (từ AI processing), MANUAL_CURATED (thủ công)
- `source_id` (`bigint`) — SOURCE: Reference ID đến record gốc (prq.address_cleansing_queue.id, mat.ward.id, etc.)
- `quality_score` (`numeric(5,4)`) — METADATA: Điểm chất lượng corpus [0-1] - dùng để filter trong retrieval
- `province_id` (`integer`) — ADMIN: ID Tỉnh/Thành phố (reference mat.province.province_id)
- `district_id` (`integer`) — ADMIN: ID Quận/Huyện (reference mat.district.district_id)
- `ward_id` (`integer`) — ADMIN: ID Phường/Xã (reference mat.ward.ward_id)
- `admin_epoch` (`character varying(10)`) — TEMPORAL: Kỳ cải cách hành chính (2025, 2026...) - support epoch-based filtering
- `admin_version` (`integer`) — TEMPORAL: Version của administrative data - track changes over time
- `effective_date` (`date`) — TEMPORAL: Ngày có hiệu lực của record corpus này
- `phobert_embedding` (`jsonb`) — EMBEDDING: Vector nhúng từ PhoBERT model stored as JSON array - pre-computed cho performance
- `mgte_embedding` (`jsonb`) — EMBEDDING: Vector nhúng từ mGTE model stored as JSON array - pre-computed cho performance
- `embedding_version` (`character varying(10)`) — EMBEDDING: Track version của embedding models (v1, v2...) để handle model updates
- `usage_count` (`bigint`) — STATS: Số lần corpus entry này được retrieve - track popularity
- `last_used_at` (`timestamp without time zone`) — STATS: Timestamp lần cuối được sử dụng - maintenance & cleanup
- `is_active` (`boolean`) — LIFECYCLE: Status active/inactive - soft delete support
- `created_by` (`character varying(50)`) — AUDIT: User/system tạo record (SYSTEM, USERNAME, etc.)

*(… còn 6 cột khác.)*

### `prq.address_cleansing_queue`

- **Loại:** table

**COMMENT ON TABLE**

Hàng đợi xử lý và chuẩn hóa địa chỉ (Hỗ trợ A/B Testing PhoBERT vs MGTE)

**Cột (mẫu / có comment)**

- `source_system` (`character varying(50)`) — Hệ thống nguồn đẩy dữ liệu vào (Ví dụ: SHOPEE, CRM_INTERNAL, TIKI)
- `raw_address` (`text`) — RAW DATA: Dữ liệu địa chỉ thô nguyên bản do khách hàng nhập
- `order_count` (`bigint`) — RAW DATA: Số lượng đơn hàng/lần xuất hiện của địa chỉ này (dùng để ưu tiên xử lý các địa chỉ lặp lại nhiều)
- `processing_status` (`character varying(30)`) — STATE: Trạng thái xử lý của luồng dữ liệu (PENDING, PROCESSING, COMPLETED, FAILED)
- `processing_method` (`character varying(30)`) — STATE: Phương pháp đã được áp dụng để xử lý (SQL_RULE, ENSEMBLE_AI, MANUAL)
- `error_message` (`text`) — STATE: Ghi nhận nguyên nhân lỗi chi tiết nếu batch bị crash hoặc chạy thất bại
- `province_id` (`integer`) — ADMIN DATA: ID Tỉnh/Thành phố (Map với master_province)
- `district_id` (`integer`) — ADMIN DATA: ID Quận/Huyện (Map với master_district)
- `ward_id` (`integer`) — ADMIN DATA: ID Phường/Xã (Map với master_ward)
- `street_address` (`text`) — CORE ADDRESS: Phần lõi địa chỉ (address_line) được bóc tách bằng SQL Rule, dùng làm input cho các mô hình AI
- `phobert_parsed_components` (`jsonb`) — AI RESULT: Kết quả bóc tách thực thể (NER) từ PhoBERT (Format: JSONB)
- `phobert_confidence_score` (`numeric(5,4)`) — AI RESULT: Độ tự tin dự đoán của mô hình PhoBERT (0.0000 -> 1.0000)
- `mgte_parsed_components` (`jsonb`) — AI RESULT: Kết quả bóc tách thực thể (NER) từ MGTE (Format: JSONB)
- `mgte_confidence_score` (`numeric(5,4)`) — AI RESULT: Độ tự tin dự đoán của mô hình MGTE (0.0000 -> 1.0000)
- `selected_ai_model` (`character varying(20)`) — DECISION: Ghi nhận AI nào (PHOBERT hoặc MGTE) đã chiến thắng dựa trên logic so sánh confidence score
- `address_standardized` (`text`) — DECISION: Chuỗi địa chỉ hoàn hảo cuối cùng được ghép lại từ kết quả NER của mô hình chiến thắng
- `phobert_embedding` (`jsonb`) — EMBEDDING: Vector nhúng sinh ra từ PhoBERT, dùng để so sánh độ tương đồng (Deduplication)
- `mgte_embedding` (`jsonb`) — EMBEDDING: Vector nhúng sinh ra từ MGTE

*(… còn 23 cột khác.)*

### `prq.address_cleansing_queue_backup_20260506_014244`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `source_system` (`character varying(50)`)
- `raw_address` (`text`)
- `order_count` (`bigint`)
- `processing_status` (`character varying(30)`)
- `processing_method` (`character varying(30)`)
- `error_message` (`text`)
- `province_id` (`integer`)
- `province_name` (`text`)
- `district_id` (`integer`)
- `district_name` (`text`)
- `ward_id` (`integer`)

*(… còn 21 cột khác.)*

### `prq.address_cleansing_queue_backup_20260510_072057`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `source_system` (`character varying(50)`)
- `raw_address` (`text`)
- `order_count` (`bigint`)
- `processing_status` (`character varying(30)`)
- `processing_method` (`character varying(30)`)
- `error_message` (`text`)
- `province_id` (`integer`)
- `province_name` (`text`)
- `district_id` (`integer`)
- `district_name` (`text`)
- `ward_id` (`integer`)

*(… còn 29 cột khác.)*

### `prq.address_cleansing_queue_backup_20260510_072119`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `source_system` (`character varying(50)`)
- `raw_address` (`text`)
- `order_count` (`bigint`)
- `processing_status` (`character varying(30)`)
- `processing_method` (`character varying(30)`)
- `error_message` (`text`)
- `province_id` (`integer`)
- `province_name` (`text`)
- `district_id` (`integer`)
- `district_name` (`text`)
- `ward_id` (`integer`)

*(… còn 29 cột khác.)*

### `prq.ground_truth`

- **Loại:** table

**COMMENT ON TABLE**

Chuẩn tham chiếu địa chỉ (Typesense/Google/manual). province_id/district_id/ward_id là mã cùng không gian với mat.*.old_id sau ánh xạ (join mat với admin_version=2). old_* là lineage tiền cải cách (join mat với admin_version=1).

**Cột (mẫu / có comment)**

- `id` (`bigint`) — PK; thường trùng document id Typesense.
- `ward_id` (`integer`) — Lineage post-reform: join mat.ward.old_id WHERE admin_version = 2.
- `district_id` (`integer`) — Lineage post-reform: join mat.district.old_id WHERE admin_version = 2.
- `province_id` (`integer`) — Lineage post-reform: join mat.province.old_id WHERE admin_version = 2 (và is_deleted).
- `old_ward_id` (`integer`) — Lineage pre-reform: join mat.ward.old_id WHERE admin_version = 1.
- `old_district_id` (`integer`) — Lineage pre-reform: join mat.district.old_id WHERE admin_version = 1.
- `old_province_id` (`integer`) — Lineage pre-reform: join mat.province.old_id WHERE admin_version = 1.
- `last_sync_run_id` (`integer`) — Khóa tới ath.typesense_ground_truth_sync_run — lần crawl gần nhất ghi nhận bản ghi này.
- `last_seen_at` (`timestamp with time zone`) — Thời điểm bản ghi được upsert từ Typesense lần cuối.

*(… còn 13 cột khác.)*

### `prq.raw_addresses`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `address_raw` (`text`)
- `status` (`character varying(20)`)
- `street_address` (`text`)
- `confidence_score` (`double precision`)
- `created_at` (`timestamp without time zone`)

### `prq.v_ground_truth_admin`

- **Loại:** view

**COMMENT ON TABLE**

Ground truth kèm tên P/D/Xã: v1 = old_* + mat admin_version=1; v2 = province_id/district_id/ward_id + mat admin_version=2. LEFT JOIN để vẫn thấy bản ghi thiếu khớp master.

**Cột (mẫu / có comment)**

- `id` (`bigint`)
- `address` (`text`)
- `old_address` (`text`)
- `address_eng` (`text`)
- `old_address_eng` (`text`)
- `latitude` (`double precision`)
- `longitude` (`double precision`)
- `popular` (`integer`)
- `source_system` (`character varying(50)`)
- `data_quality_score` (`double precision`)
- `is_validated` (`boolean`)
- `created_at` (`timestamp without time zone`)

*(… còn 15 cột khác.)*

## Schema `public`

### `public.auth_users`

- **Loại:** table

*(Không có `COMMENT ON TABLE` trong DB.)*

**Cột (mẫu / có comment)**

- `id` (`integer`)
- `username` (`character varying(100)`)
- `email` (`character varying(150)`)
- `password_hash` (`character varying(255)`)
- `display_name` (`character varying(200)`)
- `role` (`character varying(50)`)
- `is_active` (`boolean`)
- `created_at` (`timestamp without time zone`)
- `updated_at` (`timestamp without time zone`)
