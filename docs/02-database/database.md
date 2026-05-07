# Cơ sở dữ liệu PostgreSQL

Tài liệu mô tả **cấu trúc và ý nghĩa** các bảng theo mã nguồn canonical: [`app/core/database.py`](../../app/core/database.py) (SQLAlchemy). Bổ sung bảng **`prq.address_clean_corpus`** từ [`prq_address_clean_corpus.sql`](prq_address_clean_corpus.sql) (chưa có model ORM tại thời điểm ghi tài liệu).

Các schema được khởi tạo trong `Config.SCHEMAS`: `mat`, `osm`, `ath`, `prq` (xem [`app/core/config.py`](../../app/core/config.py)). Bảng **`auth_users`** nằm ở schema mặc định **`public`**.

---

## Tổng quan theo miền

| Schema | Vai trò |
|--------|---------|
| **mat** | Master data hành chính (Tỉnh/Quận/Xã), ánh xạ đổi tên–sáp nhập, ranh giới (polygon), ground truth legacy |
| **osm** | Dữ liệu làm giàu từ OpenStreetMap (đường, công trình, POI, thực thể thô) |
| **ath** | AI Training Hub, benchmark, nhật ký đồng bộ, xác thực email |
| **prq** | Hàng đợi xử lý địa chỉ, ground truth hiện hành, địa chỉ thô, corpus chuẩn (SQL) |
| **public** | Người dùng ứng dụng (`auth_users`) |

**Khóa chính lưu ý (mat):** `mat.province`, `mat.district`, `mat.ward` dùng **`row_id`** làm surrogate PK; các cột `province_id` / `district_id` / `ward_id` là **mã nghiệp vụ** (có thể lặp qua nhiều phiên bản SCD Type 2).

---

## Schema `mat` — Hành chính & ranh giới

### `mat.province`

Bản ghi **Tỉnh/Thành phố**; hỗ trợ mở rộng GSO và **SCD Type 2** (lịch sử thay đổi).

| Cột | Kiểu (ORM) | Ý nghĩa |
|-----|------------|---------|
| `row_id` | Integer PK | Khóa surrogate, tăng tự động |
| `province_id` | Integer | Mã tỉnh nghiệp vụ (bắt buộc) |
| `area_id`, `bonus_area_id` | Integer | Phân vùng / mở rộng (legacy/domain) |
| `country_id` | Integer | Quốc gia (mặc định 0) |
| `province_no` | String(20) | Mã số hiển thị |
| `province_name` | String(150) | Tên tiếng Việt |
| `type_name` | String(64) | Loại đơn vị (Thành phố, Tỉnh, …) |
| `is_default` | Boolean | Cờ mặc định hệ thống |
| `created_user`, `updated_user` | Integer | Người tạo/cập nhật |
| `created_date`, `updated_date` | DateTime | Thời điểm tạo/cập nhật |
| `is_deleted` | Boolean | Xóa mềm |
| `province_name_en` | String(200) | Tên tiếng Anh |
| `old_id` | Integer | ID DB cũ → tra `admin_unit_mapping` |
| `served_radius` | Float | Bán kính phục vụ (nếu dùng) |
| `north_pole_lat` … `west_pole_lng` | Float | Cực bounding (định vị vùng) |
| `admin_version` | Integer | Phiên bản bộ hành chính (vd. sau sáp nhập 2025) |
| `population` | BigInteger | Dân số (GSO) |
| `area_km2` | Numeric(10,2) | Diện tích km² |
| `decision_number` | String(200) | Số quyết định |
| `decision_date` | DateTime | Ngày quyết định |
| `notes` | Text | Ghi chú |
| `valid_from`, `valid_to` | DateTime | Cửa sổ hiệu lực SCD |
| `is_current` | Boolean | Bản ghi hiện hành |
| `version_id` | Integer | Số phiên bản dòng |
| `predecessor_id` | FK → `mat.province.row_id` | Liên kết bản ghi tiền nhiệm SCD |

### `mat.district`

**Quận/Huyện** thuộc tỉnh; cấu trúc tương tự tỉnh (SCD, GSO, `old_id`).

| Cột | Ý nghĩa chính |
|-----|----------------|
| `row_id` | PK surrogate |
| `district_id` | Mã quận/huyện nghiệp vụ |
| `province_id` | Thuộc tỉnh nào |
| `district_no`, `district_name`, `type_name`, `location` | Mã, tên, loại, mô tả vị trí |
| `district_name_en`, `type_name_en` | Đa ngôn ngữ |
| `sfdc_id` | Liên kết Salesforce (nếu có) |
| `is_active` | Còn hoạt động hay không |
| `admin_version` … `predecessor_id` | GSO + SCD (giống `province`) |

### `mat.ward`

**Phường/Xã** thuộc quận/huyện.

| Cột | Ý nghĩa chính |
|-----|----------------|
| `row_id` | PK surrogate |
| `ward_id` | Mã phường/xã nghiệp vụ |
| `district_id` | Thuộc quận/huyện |
| `province_no`, `ward_no` | Mã cấp trên / mã phường |
| `ward_name`, `type_name`, `location` | Tên & loại đơn vị |
| `ward_name_en`, `type_name_en` | Đa ngôn ngữ |
| `is_active` | Hoạt động |
| `admin_version` … `predecessor_id` | GSO + SCD |

### `mat.ward_mapping`

Ánh xạ **đổi đơn vị hành chính** (sáp nhập/đổi tên) theo cặp old → new.

| Cột | Ý nghĩa |
|-----|---------|
| `ward_mapping_id` | PK |
| `ward_id_old`, `province_id_old`, `district_id_old` | Đơn vị cũ |
| `ward_id_new`, `province_id_new`, `district_id_new` | Đơn vị mới |
| `effective_date_from`, `effective_date_to` | Hiệu lực |
| `relationship_type` | Kiểu quan hệ (chuỗi tự do / phân loại) |
| `mapping_total` | Thống kê ánh xạ |
| `created_*`, `updated_*`, `is_deleted`, `updated_note` | Audit |

### `mat.unit_edge`

**Đồ thị** quan hệ giữa đơn vị (không chỉ phường): sáp nhập, tách, đổi tên, chỉnh ranh.

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `from_unit_id`, `from_level` | Đơn vị nguồn (`province` / `district` / `ward`) |
| `to_unit_id`, `to_level` | Đơn vị đích |
| `relationship_type` | `MERGES_INTO`, `SPLIT_FROM`, `RENAMES_TO`, `BOUNDARY_ADJUSTED`, … |
| `effective_date` | Ngày có hiệu lực pháp lý |
| `resolution_ref` | Tham chiếu nghị quyết |
| `notes`, `created_at` | Ghi chú, thời điểm tạo |

### `mat.admin_unit_mapping`

Tra cứu **old_id → new_id** theo cấp (1=tỉnh, 2=huyện, 3=xã) và `admin_version`.

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `level` | Cấp hành chính |
| `old_id`, `new_id` | Ánh xạ ID |
| `admin_version` | Phiên bản bộ dữ liệu |
| `created_at`, `updated_at` | Audit |

### `mat.area_polygon`

**Polygon ranh giới** đơn vị (GeoJSON trong JSON; có thể bổ sung PostGIS ở DB thực tế).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `unit_level` | `province` / `district` / `ward` |
| `unit_id` | Mã đơn vị (theo nghiệp vụ) |
| `unit_name` | Tên hiển thị |
| `geojson` | Geometry dạng GeoJSON |
| `source` | `OSM`, `GSO`, `MANUAL`, … |
| `admin_version` | Phiên bản hành chính |
| `created_at`, `updated_at` | Audit |

### `mat.google_ground_truth` (legacy)

**Không khuyến nghị dùng cho code mới** — dùng `prq.ground_truth`. Giữ để tương thích migration.

Các cột: `id`, `address`, `old_address`, `ward_id`, `district_id`, `province_id`, `old_*_id`, `old_address_eng`, `address_eng`, `latitude`, `longitude`, `popular`, `created_at`, `updated_at`.

---

## Schema `osm` — OpenStreetMap

### `osm.streets`

Tuyến đường gắn **tỉnh** (làm giàu địa chỉ / gợi ý).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK (BigInteger) |
| `name` | Tên đường |
| `province_id`, `province_name` | Ngữ cảnh hành chính |
| `created_at` | Thời điểm nhập |

### `osm.buildings`

Công trình / tòa nhà (OSM).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `name`, `type` | Tên và loại OSM |
| `province_id`, `province_name` | Ngữ cảnh |
| `created_at` | Audit |

### `osm.pois`

Điểm quan tâm (POI).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `name`, `type` | Tên và loại |
| `province_id`, `province_name` | Ngữ cảnh |
| `created_at` | Audit |

### `osm.raw_entities`

Bản ghi **1-1** với thực thể OSM (node/way/relation + toàn bộ tags).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `osm_type` | `node`, `way`, `relation` |
| `tags` | JSON toàn bộ tag OSM |
| `province_id`, `province_name` | Gắn tỉnh sau khi xử lý |
| `created_at` | Audit |

---

## Schema `ath` — Training, benchmark, đồng bộ, email

### `ath.sync_log`

Nhật ký **đồng bộ / cập nhật** master hành chính (NSO, workflow, thủ công).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `sync_source` | `NSO_API`, `N8N_WORKFLOW`, `MANUAL`, … |
| `level` | `province`, `district`, `ward` |
| `unit_id` | Đơn vị liên quan |
| `change_type` | `CREATE`, `UPDATE`, `MERGE`, `RENAME`, `NO_CHANGE`, … |
| `old_value`, `new_value` | Snapshot JSON trước/sau |
| `synced_at` | Thời điểm |
| `records_affected` | Số bản ghi ảnh hưởng |
| `run_id` | Nhóm cùng một lần chạy (UUID) |

### `ath.training_datasets`

**Corpus huấn luyện NER** (câu + nhãn BIO).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `raw_text` | Văn bản địa chỉ |
| `ner_tags_json` | Token + tag BIO (JSON) |
| `is_synthetic` | Dữ liệu tổng hợp hay thật |
| `noise_level` | `low` / `medium` / `high` |
| `created_at` | Audit |

### `ath.training_history`

Snapshot **metric** theo phiên bản model.

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `version` | Nhãn phiên bản (vd. v2.3) |
| `accuracy`, `f1_score`, `loss` | Metric |
| `samples_count` | Cỡ tập |
| `created_at`, `notes` | Thời gian, ghi chú |

### `ath.benchmark_model_baselines`

**Đường cơ sở** so sánh mô hình trên dashboard (F1, throughput, cost, Google match).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `model_key` | Khóa ổn định (unique), vd. `phobert` |
| `model_name` | Tên hiển thị |
| `f1`, `throughput`, `cost_per_million`, `google_match` | Chỉ số benchmark |
| `sample_size` | Cỡ mẫu |
| `notes`, `created_at`, `updated_at` | Meta |

### `ath.benchmark_dataset`

Tập mẫu chuẩn **D1–D5** (G8): địa chỉ + kỳ vọng hành chính + loại nhiễu.

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `dataset_code` | `D1` … `D5` |
| `raw_address` | Input |
| `expected_ward_id`, `expected_district_id`, `expected_province_id` | Nhãn mong đợi |
| `noise_type` | typo, không dấu, viết tắt, pre_2025, … |
| `admin_version` | Phiên bản HC |
| `notes`, `created_at` | Ghi chú |

### `ath.benchmark_run_result`

Kết quả **một lần chạy** benchmark (theo `run_id`, `model_key`, `sample_id`).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `run_id` | UUID lần chạy |
| `dataset_code` | Bộ D |
| `model_key` | Mô hình |
| `sample_id` | FK → `ath.benchmark_dataset.id` |
| `predicted_*_id` | Dự đoán phường/huyện/tỉnh |
| `acs_score`, `acs_decision` | Điểm/quyết định tin cậy địa chỉ (G2) |
| `address_epoch` | Kỳ địa chỉ (PRE_2025 / POST_2025 / …) |
| `latency_ms` | Độ trễ |
| `is_correct` | Đúng/sai so nhãn |
| `created_at` | Audit |

### `ath.email_verifications`

**Mã OTP** xác minh email đăng ký.

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `email` | Email cần xác minh |
| `code` | Mã |
| `expires_at` | Hết hạn |
| `is_verified` | Đã xác minh |
| `created_at` | Tạo |

---

## Schema `prq` — Queue & ground truth

### `prq.address_cleansing_queue`

Hàng đợi **chuẩn hóa địa chỉ**: raw → tiền xử lý → NER (PhoBERT / mGTE) → quyết định → chuỗi chuẩn; hỗ trợ A/B embedding.

**Nhóm cột:**

1. **Input:** `source_system`, `raw_address`, `order_count`
2. **Trạng thái:** `processing_status` (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, …), `processing_method` (`SQL_RULE`, `ENSEMBLE_AI`, `MANUAL`, …), `error_message`
3. **Hành chính (đã map):** `province_id/name`, `district_id/name`, `ward_id/name`
4. **Lineage (ID cũ / pre-map):** `old_province_id`, `old_district_id`, `old_ward_id` — join `mat.*.old_id` hoặc `admin_unit_mapping`
5. **Lõi đường phố:** `street_address` (thường từ SQL rule), `normalized_phobert`, `normalized_mgte`
6. **AI:** `phobert_parsed_components`, `phobert_confidence_score`, `mgte_parsed_components`, `mgte_confidence_score` (JSON + score 0–1)
7. **Quyết định:** `selected_ai_model`, `address_standardized`
8. **Địa lý thương mại:** `postal_code`, `country_code`, `latitude`, `longitude`
9. **Embedding (JSON trong ORM):** `phobert_embedding`, `mgte_embedding`
10. **Audit:** `created_at`, `updated_at`

**Lưu ý:** Trong ORM có comment các cột **ACS** (G2) và **address_epoch** (G5) — có thể được thêm bằng migration SQL sau; khi có trong DB, bổ sung cùng ý nghĩa trong bảng này.

**Index tham khảo:** `idx_address_status` trên `processing_status` (theo script DDL thủ công / migration).

### `prq.raw_addresses`

Bảng **địa chỉ thô** nhẹ (luồng xử lý đơn giản / staging).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `raw_address` | Chuỗi gốc |
| `status` | `pending`, `ai_processed`, `human_reviewed`, `completed`, … |
| `street_address` | Đã tách đường (nếu có) |
| `confidence_score` | Độ tin cậy |
| `created_at` | Audit |

### `prq.ground_truth`

**Chuẩn tham chiếu** địa chỉ (Typesense/Google/manual): dùng cho đánh giá, retrieval, sync.

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK (BigInteger, thường trùng id nguồn Typesense) |
| `address` | Địa chỉ chuẩn (VN) |
| `old_address` | Bản thô / trước chuẩn hóa |
| `ward_id`, `district_id`, `province_id` | **Lineage sau ánh xạ:** cùng không gian với `mat.*.old_id`, join `mat` với **`admin_version = 2`** (không phải `mat.ward.ward_id` nội bộ) |
| `old_ward_id`, `old_district_id`, `old_province_id` | **Lineage tiền cải cách / field gốc:** join `mat.*.old_id` với **`admin_version = 1`** (khi thiếu trên document crawl, điền từ raw `province_id`/`district_id`/`ward_id` chưa map) |
| `old_address_eng`, `address_eng` | Tiếng Anh |
| `latitude`, `longitude` | Tọa độ |
| `popular` | Độ phổ biến / hit |
| `source_system` | `TYPESENSE`, `GOOGLE`, `MANUAL`, … |
| `data_quality_score` | Chất lượng 0–1 |
| `is_validated`, `validation_notes` | Kiểm định người |
| `last_sync_run_id`, `last_seen_at` | Audit crawl Typesense → FK/lần chạm (`ath.typesense_ground_truth_sync_run`); thêm bằng migration SQL |
| `created_at`, `updated_at` | Audit |

**View:** `prq.v_ground_truth_admin` — một dòng GT + tên P/D/Xã cho cả hai kỳ HC (v1/v2); xem [`scripts/sql/prq_ground_truth_admin_view.sql`](scripts/sql/prq_ground_truth_admin_view.sql).

**Collection Typesense (tài liệu field):** [`docs/typesense/google_addresses.schema.json`](typesense/google_addresses.schema.json).

**Index ORM:** theo `province_id`, `district_id`, `ward_id`, `(latitude, longitude)`.

### `prq.address_clean_corpus` (SQL — corpus Siamese / retrieval)

Định nghĩa trong [`prq_address_clean_corpus.sql`](prq_address_clean_corpus.sql). Mục đích: **corpus địa chỉ sạch** + embedding (`vector(768)` nếu bật pgvector).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK bigserial |
| `standardized_address` | Chuỗi chuẩn đầy đủ |
| `address_components` | JSON chi tiết (số nhà, đường, …) |
| `source_type` | `ADMINISTRATIVE`, `QUEUE_STANDARDIZED`, `MANUAL_CURATED` |
| `source_id` | Tham chiếu bản ghi nguồn (queue, ward, …) |
| `quality_score` | 0–1 |
| `province_*`, `district_*`, `ward_*` | Ngữ cảnh HC |
| `admin_epoch` | Kỳ cải cách (`2023`–`2026` theo CHECK) |
| `admin_version` | Phiên bản HC |
| `effective_date` | Ngày hiệu lực logic |
| `phobert_embedding`, `mgte_embedding` | Vector pgvector (768 chiều) |
| `embedding_version` | Phiên bản pipeline embedding |
| `usage_count`, `last_used_at` | Thống kê retrieval |
| `is_active` | Kích hoạt corpus |
| `created_at`, `updated_at`, `created_by` | Audit |

**Ràng buộc:** UNIQUE `(standardized_address, admin_epoch, source_type)`; CHECK `quality_score`, `source_type`, `admin_epoch`.

Bản [`prq_address_clean_corpus_no_vector.sql`](prq_address_clean_corpus_no_vector.sql) tương tự nhưng **không** dùng kiểu `vector` (môi trường chưa cài pgvector).

---

## Schema `public` — Người dùng

### `public.auth_users`

Tài khoản **đăng nhập ứng dụng** (không gán schema trong ORM → `public`).

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `username` | Đăng nhập (unique, index) |
| `email` | Email (unique, index) |
| `password_hash` | Hash mật khẩu |
| `display_name` | Tên hiển thị |
| `role` | Vai trò (vd. `user`, `admin`) |
| `is_active` | Khóa tài khoản |
| `created_at`, `updated_at` | Audit |

---

## Tham chiếu nhanh: quan hệ logic

- **`prq.address_cleansing_queue`**: `province_id` / `district_id` / `ward_id` → **`mat.province` / `district` / `ward`** theo `province_id`/`district_id`/`ward_id` **và** nên lọc `is_current = true` khi cần bản ghi hiện hành.
- **Lineage:** `old_*_id` trên queue hoặc ground truth → **`mat.admin_unit_mapping`** hoặc `mat.*.old_id`.
- **Lịch sử sáp nhập:** **`mat.unit_edge`**, **`mat.ward_mapping`**.
- **GT đánh giá:** **`prq.ground_truth`** (ưu tiên) so với **`mat.google_ground_truth`** (legacy).
- **OSM:** Các bảng `osm.*` làm giàu địa chỉ / POI / ranh giới (kết hợp `mat.area_polygon`).

---

*Tài liệu đồng bộ với codebase tại nhánh làm việc hiện tại. Nếu migration SQL thêm cột mà ORM chưa kịp cập nhật, ưu tiên kiểm tra trực tiếp PostgreSQL (`information_schema` / `\d+ schema.table`).*
