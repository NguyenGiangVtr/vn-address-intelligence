# TODO — VN Address Intelligence
> Dựa trên phân tích `docs/feature-status-analysis.md` | Cập nhật: 04/05/2026

---

## ✅ HOÀN THÀNH

- [x] Review numeric logger statements in `app/ai/production_pipeline.py`
- [x] Apply formatted-number logging (`:,`) for all numeric values in log messages
- [x] Verify consistency of number formatting across log lines
- [x] Update NER loading flow to avoid loading `vinai/phobert-base` for token-classification when fine-tuned model is missing
- [x] Improve NER logging message to clarify fallback behavior (Regex fallback, not model error)
- [x] Update pipeline initialization to pass only local fine-tuned path (or force fallback)
- [x] Mark completion after quick consistency review
- [x] Update admin units grid column: replace "Tên Tiếng Anh" with "Ngày cập nhật (updated_date)"
- [x] Verify header label and row binding are updated in ui/app.js
- [x] Standardize parser page wording for scientific research + SaaS context
- [x] Standardize parser-footer-row UI structure and styling
- [x] **[G1]** Thêm SCD Type 2 columns vào `mat.province`, `mat.district`, `mat.ward` (`valid_from`, `valid_to`, `is_current`, `version_id`, `predecessor_id`)
- [x] **[G1]** Tạo bảng `mat.unit_edge` — đồ thị quan hệ hành chính (MERGES_INTO, SPLIT_FROM, RENAMES_TO…)
- [x] **[G1]** Tạo bảng `ath.sync_log` — nhật ký đồng bộ persist theo `run_id`
- [x] **[G1]** Tạo `app/services/scd_sync.py` — SCD Type 2 upsert logic (checksum-based)
- [x] **[G1]** Nâng cấp n8n workflow: thêm Sync Log Insert + Email Alert nodes sau khi hoàn thành 34 tỉnh
- [x] **[G1]** Tạo `scripts/migration/scd_type2_migration.sql` — migration SQL + views
- [x] **[G1]** `GET /api/admin-unit/{level}/{unit_id}/history` — point-in-time SCD history endpoint
- [x] **[G1]** `GET /api/sync-logs` + `GET /api/sync-logs/summary/{run_id}` — nhật ký đồng bộ

---

## 🔴 P0 — CẦN THIẾT CHO LUẬN VĂN (ưu tiên cao nhất)

### G2. Address Confidence Score (ACS) đầy đủ
> Chương 2.4.5 — core concept | ~6 ngày

- [ ] Tạo `app/ai/acs_calculator.py` với class `ACSCalculator` và `ACSComponents`
- [ ] Implement `validate_hierarchy()` — kiểm tra Phường ∈ Huyện ∈ Tỉnh trong `mat.*`
- [ ] Implement `compute_temporal_weight()` — phạt nhẹ địa chỉ admin version cũ
- [ ] Implement `get_decision()` — bảng quyết định ACS (≥0.9 Auto-Accept | 0.7-0.9 Auto-Convert | 0.5-0.7 Suggest | <0.5 Reject)
- [ ] Tích hợp ACS vào `app/ai/production_pipeline.py`
- [ ] Migration: thêm cột `acs_score`, `acs_decision`, `s_text`, `s_sem`, `v_hierarchy`, `v_temporal` vào `prq.address_cleansing_queue`
- [ ] Cập nhật response của `POST /api/parser/analyze` để bao gồm `acs_score` và `acs_decision`

### G5. Temporal-Aware Address — Dual-Epoch Recognition
> Chương 1.1.3, 2.4.3 — novelty | ~6 ngày

- [ ] Tạo `app/ai/epoch_detector.py` — phát hiện địa chỉ Pre-2025 / Post-2025 / Ambiguous
- [ ] Load từ khóa Pre-2025 (quận, huyện, thị xã…) và tên đơn vị Post-2025 từ DB
- [ ] Cập nhật `app/ai/models/siamese_mgte.py` — `match_with_temporal()` với temporal corpus filter
- [ ] Tích hợp epoch detector vào `production_pipeline.py`
- [ ] Tạo `POST /api/migrate-address` — chuyển đổi địa chỉ Pre-2025 → Post-2025
- [ ] Migration: thêm cột `address_epoch VARCHAR(20)` vào `prq.address_cleansing_queue`

### G3. Geospatial API — Point-in-Polygon
> Chương 2.5, 3.4 — thực nghiệm | ~13 ngày

- [ ] Xác nhận PostGIS extension đã cài trên PostgreSQL
- [ ] Tạo/xác nhận bảng `mat.area_polygon` đúng schema + spatial index GIST
- [ ] Import GeoJSON polygon từ OSM/GSO vào `mat.area_polygon`
- [ ] Tạo `app/api/spatial.py` — Spatial API router
- [ ] Implement `POST /api/spatial/subdivide` — Point-in-Polygon batch với fallback ST_Distance nearest
- [ ] Tạo `app/geometry/buffer_union.py` — Chiến lược 1: Buffer union correction
- [ ] Tạo `app/geometry/concave_hull.py` — Chiến lược 2: Concave hull từ đám mây điểm
- [ ] Tạo `app/geometry/edge_inject.py` — Chiến lược 3: Edge inject correction
- [ ] Tạo `app/services/spatial_mismatch.py` — Mismatch Analysis Pipeline từ CSV đơn hàng
- [ ] Thêm `mat.area_polygon` ORM model vào `database.py`
- [ ] `GET /api/spatial/mismatch-report` endpoint

---

## 🟠 P1 — QUAN TRỌNG

### G1. n8n GOV-SYNC (còn lại)
- [ ] Cập nhật `docker-compose.yml` với n8n service (nếu chưa có)
- [ ] Tích hợp Typesense upsert vào n8n workflow sau khi sync PostgreSQL (sau khi G9 xong)

### G8. Benchmark D1-D5 chuẩn
> Chương 4.1 — thực nghiệm | ~7 ngày

- [ ] Tạo bảng `ath.benchmark_dataset` (D1-D5 schema)
- [ ] Tạo bảng `ath.benchmark_run_result`
- [ ] Tạo `scripts/generate_benchmark_datasets.py`
  - [ ] `generate_d1_urban()` — 2,000 mẫu đô thị chuẩn (mat.ward admin_version=2)
  - [ ] `generate_d2_noisy()` — 1,000 mẫu nhiễu cao (typo, bỏ dấu, viết tắt)
  - [ ] `generate_d3_pre2025()` — 1,000 mẫu Pre-2025 (admin_version=1)
  - [ ] `generate_d4_rural()` — 1,000 mẫu nông thôn (thôn/xóm/ấp, thiếu số nhà)
  - [ ] `generate_d5_boundary()` — 1,000 mẫu ranh giới (GPS gần biên polygon)
- [ ] Tích hợp D1-D5 vào `experiment_runner.py`
- [ ] `GET /api/benchmark/datasets` endpoint

---

## 🟡 P2 — NÊN CÓ

### G7. Training Pipeline PhoBERT NER thực sự
> Chương 2.4.2, 3.3.2 | ~7 ngày

- [ ] Export annotation từ Label Studio → BIO format
- [ ] Split dataset 80/10/10 (train/dev/test) và lưu vào `ath.training_datasets`
- [ ] Tạo `app/ai/models/ner_bilstm_crf.py` — PhoBERT + BiLSTM-CRF architecture
- [ ] Cập nhật `app/ai/train_ner.py` dùng model PhoBERT BiLSTM-CRF mới
- [ ] Script data augmentation (viết tắt, không dấu, hoán đổi thứ tự)

### G4. Waterfall Enrichment (Redis → OSM → VietMap → Google)
> Chương 2.6, 5.1 | ~8 ngày

- [ ] Thêm Redis service vào `docker-compose.yml`
- [ ] Thêm `REDIS_HOST`, `REDIS_PORT`, `REDIS_TTL_SECONDS` vào `app/core/config.py`
- [ ] Tạo `app/services/waterfall_enrichment.py` — `WaterfallEnrichmentService` (L1-L4)
- [ ] Implement `_lookup_osm()` — tìm trong `osm.streets`, `osm.pois`
- [ ] Implement `_call_vietmap()` — VietMap API integration
- [ ] Implement `_call_google_geocoding()` — Google Maps Geocoding API (ROOFTOP/RANGE_INTERPOLATED/GEOMETRIC_CENTER/APPROXIMATE)
- [ ] Đăng ký API keys: Google Maps, VietMap
- [ ] Tạo bảng `ath.enrichment_metrics` — theo dõi hit rate per source per day
- [ ] `POST /api/enrich` endpoint
- [ ] Cập nhật `GET /api/enrichment/summary` với hit rate per source

### G6. FAISS Vector Index cho Siamese Matching
> Chương 3.3.3 | ~5 ngày

- [ ] `pip install faiss-cpu` (hoặc faiss-gpu)
- [ ] Tạo `app/ai/faiss_index.py` — `AdminUnitFAISSIndex` (IVFHNSW)
- [ ] Tích hợp FAISS vào `app/ai/models/siamese_mgte.py` — thay brute-force cosine
- [ ] `POST /api/admin/rebuild-index` endpoint — trigger rebuild background
- [ ] CLI: `python app/main.py admin:rebuild-index`

---

## 🟢 P3 — THẤP / TƯƠNG LAI

### G9. Typesense Search Index Integration
> Chương 2.2.1 | ~4 ngày

- [ ] Tạo `app/services/typesense_sync.py` — collection schema + `sync_mat_to_typesense()`
- [ ] `POST /api/admin/sync-typesense` endpoint
- [ ] Tích hợp vào n8n workflow G1 (Typesense upsert sau sync PostgreSQL)

### G10. Định hướng phát triển (roadmap dài hạn, không cần cho luận văn)
- [ ] H1: Ensemble Model (PhoBERT + mGTE + Qwen3 với Confidence routing)
- [ ] H2: NLP trích xuất thay đổi hành chính từ PDF Nghị quyết
- [ ] H3: Reverse Geocoding đến số nhà + GNN
- [ ] H4: Privacy-Preserving (Federated Learning)
- [ ] H5: Multimodal (ASR + OCR địa chỉ)

---

## ⚙️ ĐIỀU KIỆN TIÊN QUYẾT CẦN XÁC NHẬN

- [ ] Xác nhận PostGIS extension đã cài: `CREATE EXTENSION IF NOT EXISTS postgis;`
- [ ] Import GeoJSON polygon dữ liệu vào `mat.area_polygon` (từ OSM/GSO)
- [ ] Xác nhận GPU cho PhoBERT training (hoặc Google Colab setup)
- [ ] Đăng ký Google Maps API Key và cấu hình `.env`
- [ ] Đăng ký VietMap API Key và cấu hình `.env`
- [ ] Gán nhãn thủ công thêm mẫu địa chỉ trong Label Studio (mục tiêu 100k+ mẫu)
- [ ] Chạy migration SCD Type 2: `scripts/migration/scd_type2_migration.sql`

---

## 📊 TIẾN ĐỘ TỔNG QUAN

| Module | Hoàn thành |
|--------|-----------|
| M1 Gov-Sync (n8n) | 95% ✅ |
| M2 AI Pipeline | 75% |
| M2a ACS Score | 30% 🔴 |
| M3 Geospatial | 35% 🔴 |
| M4 Enrichment | 50% 🟡 |
| Web UI | 90% ✅ |
| REST API | 80% |
| Database | 70% |
