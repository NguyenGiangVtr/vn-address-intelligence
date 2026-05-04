# TÀI LIỆU THỐNG KÊ TÍNH NĂNG DỰ ÁN VNAI
## Đã đáp ứng vs. Chưa đáp ứng — Đối chiếu với Dàn ý Luận văn

> **Phiên bản:** 1.1 | **Ngày:** 04/05/2026 (cập nhật: n8n NSO crawler đã hoàn chỉnh)  
> **Luận văn:** Xây dựng Khung Giải pháp Làm giàu và Chuẩn hóa Dữ liệu Địa chỉ Việt Nam  
> **Repository:** `https://github.com/NguyenGiangVtr/vn-address-intelligence`

---

## MỤC LỤC

1. [Tổng quan mức độ đáp ứng](#1-tổng-quan-mức-độ-đáp-ứng)
2. [Phần I — Tính năng ĐÃ ĐÁP ỨNG (chi tiết hoạt động)](#2-phần-i--tính-năng-đã-đáp-ứng)
3. [Phần II — Tính năng CHƯA ĐÁP ỨNG (kế hoạch thực hiện)](#3-phần-ii--tính-năng-chưa-đáp-ứng)
4. [Ma trận rủi ro & ưu tiên](#4-ma-trận-rủi-ro--ưu-tiên)

---

## 1. TỔNG QUAN MỨC ĐỘ ĐÁP ỨNG

### 1.1 Bảng tổng hợp theo Business Requirement

| BR# | Yêu cầu nghiệp vụ | Trạng thái | Mức độ hoàn thiện |
|-----|-------------------|------------|-------------------|
| BR1 | Đồng bộ hành chính tự động từ nguồn Chính phủ | ✅ Tốt | 80% — n8n Browserless crawler có, chạy cron 01:00 AM, SCD Type 2 đầy đủ **chưa có** |
| BR2 | Chuẩn hóa địa chỉ thô → cấu trúc chuẩn + GSOID | ✅ Cơ bản | 70% — pipeline AI hoạt động, ACS đầy đủ **chưa có** |
| BR3 | Tra cứu lịch sử hành chính, ánh xạ địa chỉ cũ→mới | ⚠️ Một phần | 50% — `mat.ward_mapping` có, SCD Type 2 đầy đủ **chưa có** |
| BR4 | Xác định đơn vị hành chính từ tọa độ (Point-in-Polygon) | ⚠️ Một phần | 40% — polygon visualization có, API `/subdivide` **chưa có** |
| BR5 | Làm giàu dữ liệu từ đa nguồn (OSM, Google, VietMap) | ⚠️ Một phần | 60% — OSM fetcher có, Waterfall strategy **chưa hoàn chỉnh** |
| BR6 | Nền tảng benchmark liên tục so sánh mô hình AI | ✅ Tốt | 85% — experiment runner + UI benchmark đầy đủ |

### 1.2 Bảng tổng hợp theo Module kiến trúc

| Module | Mô tả luận văn | Thực tế codebase | % Hoàn thành |
|--------|---------------|-----------------|--------------|
| **M1** Gov-Sync (n8n) | n8n workflow: SOAP→SCD Type 2→Typesense | **n8n Browserless crawler hoạt động** (cron 01:00 AM, index 0→33 tỉnh, UPDATE `mat.ward`) | 70% |
| **M2** AI Pipeline | PhoBERT NER → mGTE Siamese → Qwen3 LLM | Cả 3 model có, production pipeline có | 75% |
| **M2a** ACS Score | Công thức 4 thành phần (text+sem+hier+temporal) | Chỉ confidence score đơn giản | 30% |
| **M3** Geospatial | Point-in-Polygon, 3 chiến lược hiệu chỉnh polygon | Boundary visualization, chưa có API subdivide | 35% |
| **M4** Enrichment | Waterfall: Redis→OSM→Google→Typesense | OSM fetcher + basic enrichment | 50% |
| **Web UI** | explorer, benchmark, admin_units pages | 15+ trang UI hoàn chỉnh | 90% |
| **REST API** | FastAPI endpoints đầy đủ | 30+ endpoints, thiếu spatial endpoints | 80% |
| **Database** | 4 schema: mat, osm, ath, prq | Đã tạo đầy đủ, thiếu một số bảng | 70% |

---

## 2. PHẦN I — TÍNH NĂNG ĐÃ ĐÁP ỨNG

---

### F1. HỆ THỐNG ĐĂNG NHẬP VÀ XÁC THỰC (Authentication)

**Trạng thái:** ✅ Hoàn chỉnh

#### Input
- `POST /api/login`: `{username, password}` (OAuth2 form)
- `POST /api/register/send-code`: `{email}` — gửi code xác thực
- `POST /api/register`: `{email, code, username, password}`

#### Process
1. `app/services/auth.py`: `bcrypt` hash password → verify
2. JWT token tạo với `python-jose` (HS256), TTL cấu hình từ `.env`
3. Email verification: random 6-digit code → SMTP gửi HTML email (`app/services/email_service.py`)
4. Code lưu bảng `ath.email_verifications` với `expires_at`

#### Output
- JWT access token (JSON response)
- Redirect về dashboard sau đăng nhập thành công

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `public` | `auth_users` | Lưu username, email, password_hash, role |
| `ath` | `email_verifications` | Lưu OTP code + trạng thái xác thực |

---

### F2. QUẢN LÝ DANH MỤC ĐƠN VỊ HÀNH CHÍNH (Admin Units CRUD)

**Trạng thái:** ✅ Hoàn chỉnh

#### Input
- `GET /api/provinces` — danh sách tỉnh (query: `version=1|2`, `search`)
- `GET /api/districts` — danh sách huyện (query: `province_id`)
- `GET /api/wards` — danh sách xã/phường (query: `district_id`)
- `GET /api/unit-details/{level}/{unit_id}` — chi tiết 1 đơn vị

#### Process
1. SQLAlchemy query vào `mat.province`, `mat.district`, `mat.ward`
2. Hỗ trợ filter theo `admin_version` (v1 = trước sáp nhập, v2 = sau 07/2025)
3. Join với bảng ánh xạ `mat.ward_mapping` để lấy thông tin sáp nhập

#### Output
```json
{
  "province_id": 79,
  "province_name": "Thành phố Hồ Chí Minh",
  "admin_version": 2,
  "population": 9000000,
  "area_km2": 2061.22
}
```

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `mat` | `province` | Master dữ liệu tỉnh (có `old_id`, `admin_version`) |
| `mat` | `district` | Master dữ liệu huyện (lịch sử) |
| `mat` | `ward` | Master dữ liệu xã/phường (có `admin_version`) |
| `mat` | `ward_mapping` | Ánh xạ đơn vị cũ → mới (`relationship_type`, `effective_date_from`) |

---

### F3. ĐỒNG BỘ DỮ LIỆU TỪ NGUỒN NSO (NSO Sync — n8n Browserless Crawler)

**Trạng thái:** ✅ Tốt (n8n workflow hoạt động, SCD Type 2 chưa đầy đủ)

#### Input
- **Trigger tự động:** Cron `01:00 AM` hàng ngày (n8n Schedule node)
- **Nguồn:** `danhmuchanhchinh.nso.gov.vn` — duyệt theo chỉ số (index) tỉnh từ `0` đến `33`
- `POST /api/sync/nso` — trigger thủ công qua API (Python fallback)
- `POST /api/sync/nso/province` — đồng bộ thủ công 1 tỉnh cụ thể

> **Workflow file:** `docs/n8n/Automated Geospatial Data Extraction and Synchronization System.json`  
> **Workflow ID:** `S5smdRYjLEmaaMKp` | **Active:** `true` | **Cron:** `01:00 AM daily`

#### Process (n8n Workflow — các nodes thực tế)

```
[Schedule Trigger: 01:00 AM]  +  [Manual Trigger: Execute workflow]
              ↓
[Global Parameter Configuration]
  • browserlessUrl = http://browserless:3000
  • token = e1ec2096...
  • filePath = /home/node/.n8n/danhmuc_hanhchinh.json
              ↓
[Cache/Storage Sanitization]
  ← fs.unlinkSync(filePath) — xóa JSON tạm từ phiên cũ
              ↓
[Index Range Generation]
  ← Sinh 34 items: [{index: 0}, {index: 1}, ..., {index: 33}]
              ↓
[Iteration Controller] ← SplitInBatches
              ↓
[Web Scraper / Data Extraction Service]
  ← POST browserless /function với Puppeteer script:
    • Mở danhmuchanhchinh.nso.gov.vn
    • Click hàng tỉnh theo index
    • Lặp qua từng đơn vị cấp dưới (childCount rows)
    • Extract: ma, ten, tenAnh, cap, ngayQuyetDinh,
               ngayHieuLuc, danSo, dienTich, ghiChu
              ↓
[Data Normalization & Transformation]
  ← Đọc JSON file tạm → concat dữ liệu tỉnh mới → ghi lại file
              ↓
[Relational Database Persistence] ← PostgreSQL node
  UPDATE mat.ward SET
    province_no, ward_name, ward_name_en, type_name,
    decision_date, effective_date, population, area_km2, notes,
    updated_date = NOW()
  WHERE ward_no = :ma AND admin_version = 2
              ↓
  [loop back → Iteration Controller]
```

Bên cạnh n8n, Python services vẫn duy trì:
1. `app/services/nso_api.py`: HTTP REST client với retry
2. `app/services/nso_sync.py`: parse response, upsert vào `mat.*`
3. `app/services/seeders_v3.py`: seeding dữ liệu ban đầu từ file tĩnh

#### Output
- Bảng `mat.ward` được UPDATE các trường: `ward_name_en`, `decision_date`, `population`, `area_km2`, lọc theo `ward_no` và `admin_version = 2`
- `GET /api/sync/nso/logs`: log buffer trạng thái đồng bộ

#### Tables liên quan
| Schema | Bảng | Cột được cập nhật | Điều kiện |
|--------|------|-------------------|-----------|
| `mat` | `ward` | `ward_name`, `ward_name_en`, `type_name`, `decision_date`, `population`, `area_km2` | `ward_no = :code AND admin_version = 2` |
| `mat` | `province` | Upsert toàn bộ qua Python fallback | `province_id` conflict |
| `mat` | `district` | Upsert toàn bộ qua Python fallback | `district_id` conflict |

#### Khoảng trống còn lại
- ⚠️ **Chưa có SCD Type 2** — UPDATE trực tiếp, không đóng bản ghi lịch sử cũ
- ⚠️ **Chưa persist sync_log** vào DB (in-memory list, mất khi restart)
- ⚠️ **Chưa kết nối Cổng DVC SOAP** — chỉ scrape web NSO, không qua API chính thức
- ⚠️ **Chưa sync Typesense** sau khi cập nhật DB

---

### F4. PIPELINE AI CHUẨN HÓA ĐỊA CHỈ (Address Normalization Pipeline)

**Trạng thái:** ✅ Cơ bản (3 model có, ghép nối production pipeline có)

#### 4a. Tiền xử lý (Preprocessing)

##### Input
- Chuỗi địa chỉ thô (free-text), ví dụ: `"90/12 ly thuong kiet q.TB HCM"`

##### Process (`app/ai/utils/address_cleaner.py`)
1. Unicode NFC normalization (xử lý NFD từ iOS/macOS)
2. Viết tắt expansion: `"Q." → "Quận"`, `"P." → "Phường"`, `"TP." → "Thành phố"` (200+ entry)
3. Regex chuẩn hóa cấu trúc ngõ/ngách: `"90/12/5"` → `{street: 90, alley: 12, house: 5}`
4. Tích hợp `vnauto` cho teencode, thiếu dấu

##### Output
```python
{"cleaned": "90/12 Lý Thường Kiệt, Quận Tân Bình, Thành phố Hồ Chí Minh"}
```

##### Tables liên quan
- Không lưu DB — xử lý in-memory

---

#### 4b. PhoBERT NER (Entity Recognition)

##### Input
- Chuỗi địa chỉ đã tiền xử lý

##### Process (`app/ai/models/phobert_model.py`)
1. `SentenceTransformer` với backbone PhoBERT (`vinai/phobert-base`)
2. Optional PyVi word segmentation trước khi encode
3. Cosine similarity matching với corpus đã build từ `mat.ward/district/province`
4. Token classification pipeline nếu dùng `models/ner_model.py` (`AddressNER`)

##### Output
```json
{
  "phobert_parsed_components": {
    "province": "Hồ Chí Minh", 
    "district": "Tân Bình",
    "ward": "Phường 12",
    "street": "Lý Thường Kiệt",
    "house_number": "90/12"
  },
  "phobert_confidence_score": 0.8720
}
```

##### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `mat` | `province/district/ward` | Corpus để build embedding index |
| `prq` | `address_cleansing_queue` | Lưu `phobert_parsed_components`, `phobert_confidence_score` |

---

#### 4c. mGTE Siamese Matching

##### Input
- Tên đơn vị hành chính trích xuất từ NER
- Corpus từ `mat.*`

##### Process (`app/ai/models/siamese_mgte.py`)
1. `SiameseMGTE` encode query + corpus bằng multilingual GTE
2. Cosine similarity → top-k candidates
3. FAISS IVFHNSW cho Approximate Nearest Neighbor (thiết kế, chưa tích hợp FAISS thực tế)
4. Fuzzy Matching bổ sung cho sai chính tả nhẹ

##### Output
```json
{
  "mgte_parsed_components": {...},
  "mgte_confidence_score": 0.9130,
  "mgte_embedding": [0.123, -0.456, ...]
}
```

##### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `prq` | `address_cleansing_queue` | Lưu `mgte_parsed_components`, `mgte_embedding` |
| `mat` | `ward/district/province` | Source corpus embedding |

---

#### 4d. Qwen3 LLM Refinement

##### Input
- Địa chỉ phức tạp (confidence thấp < ngưỡng)
- Few-shot prompt template tiếng Việt

##### Process (`app/ai/models/llm_model.py`)
1. `LLMQwen3`: HuggingFace CausalLM pipeline (`Qwen/Qwen3-*`)
2. Structured prompt yêu cầu JSON output theo schema cố định
3. Constrained decoding (JSON schema enforcement)
4. Result caching cho pattern lặp lại (thiết kế)

##### Output
```json
{
  "house_number": "90/12",
  "street": "Lý Thường Kiệt",
  "ward": "Phường 12",
  "district": "Tân Bình",
  "province": "Hồ Chí Minh",
  "confidence": 0.89
}
```

##### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `prq` | `address_cleansing_queue` | Input từ queue, output lưu `address_standardized` |

---

#### 4e. Production Pipeline (Batch Processing)

##### Input
- `POST /api/batch/trigger` — trigger background job
- Hoặc CLI: `python app/main.py data:generate`

##### Process (`app/ai/production_pipeline.py`)
1. Đọc records từ `prq.address_cleansing_queue` có `status = 'PENDING'`
2. Build mGTE corpus từ `mat.*`
3. NER → mGTE Siamese → quyết định model thắng
4. Update record với kết quả + `selected_ai_model`

##### Output
- Records trong `prq.address_cleansing_queue` được update `processing_status = 'COMPLETED'`
- `GET /api/batch/job` — trạng thái job

##### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `prq` | `address_cleansing_queue` | Read PENDING → Write COMPLETED |
| `mat` | `province/district/ward` | Corpus source |
| `ath` | `training_datasets` | Training data management |

---

### F5. PARSER API — PHÂN TÍCH ĐỊA CHỈ ĐƠN (Real-time Parser)

**Trạng thái:** ✅ Hoàn chỉnh

#### Input
```http
POST /api/parser/analyze
{
  "raw_address": "90 Ly Thuong Kiet Q.TB HCM",
  "model": "phobert|mgte|llm|all"
}
```

#### Process (`app/api/server.py` — `/parser/analyze` endpoint)
1. Tiền xử lý địa chỉ
2. Chạy model được chọn (hoặc tất cả nếu `model=all`)
3. So sánh kết quả các model (multi-model comparison)
4. Trả về kết quả có structured JSON + confidence score mỗi model

#### Output
```json
{
  "input": "90 Ly Thuong Kiet Q.TB HCM",
  "models": {
    "phobert": {"components": {...}, "confidence": 0.87, "latency_ms": 85},
    "mgte":    {"components": {...}, "confidence": 0.91, "latency_ms": 72},
    "llm":     {"components": {...}, "confidence": 0.94, "latency_ms": 480}
  },
  "winner": "mgte"
}
```

#### Tables liên quan
- Không ghi DB (real-time only), tùy chọn log vào `prq.address_cleansing_queue`

---

### F6. HỆ THỐNG BENCHMARK VÀ ĐO LƯỜNG HIỆU NĂNG

**Trạng thái:** ✅ Tốt

#### Input
- `POST /api/benchmark/trigger` — trigger chạy experiment
- `GET /api/benchmark/realtime` — metrics realtime
- `GET /api/benchmark/baselines` — lịch sử baseline

#### Process (`app/ai/experiment_runner.py`)
1. Load config từ `app/ai/config.yaml`
2. Chạy multi-model inference trên test set
3. Tính F1 Score, Exact Match, Throughput, P95 Latency
4. Upsert kết quả vào `ath.benchmark_model_baselines`
5. Generate HTML/CSV report (`app/ai/report_generator.py`)

#### Output
```json
{
  "phobert": {"f1": 84.2, "throughput": 27.8, "p95_latency": 85, "cost_per_million": 42},
  "mgte":    {"f1": 81.3, "throughput": 31.6, "p95_latency": 72, "cost_per_million": 28},
  "llm":     {"f1": 86.8, "throughput": 9.4,  "p95_latency": 480, "cost_per_million": 260}
}
```

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `ath` | `benchmark_model_baselines` | Lưu F1, throughput, cost/M samples |
| `ath` | `training_history` | Lịch sử version model và accuracy |

---

### F7. THU THẬP DỮ LIỆU OSM (OpenStreetMap Fetcher)

**Trạng thái:** ✅ Cơ bản

#### Input
- `POST /api/osm/trigger` — trigger background job
- CLI: `python app/main.py osm:fetch --province-id 79`

#### Process (`app/services/osm_fetcher.py`)
1. Gọi Overpass API với bounding box của từng tỉnh
2. Parse XML response lấy nodes/ways với tags `highway`, `building`, `amenity`
3. Lưu vào `osm.streets`, `osm.buildings`, `osm.pois`

#### Output
- Rows trong `osm.*` tables
- `GET /api/osm/summary` — count by table
- `GET /api/osm/preview` — sample rows

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `osm` | `streets` | Tên đường từ OSM |
| `osm` | `buildings` | Tòa nhà, công trình |
| `osm` | `pois` | Điểm quan tâm |
| `osm` | `raw_entities` | Lưu raw OSM tags (JSON) |

---

### F8. TRỰC QUAN HÓA RANH GIỚI POLYGON (Boundary Visualization)

**Trạng thái:** ✅ Cơ bản

#### Input
- `GET /api/boundary/map?province_id=79&district_id=770`

#### Process (`app/api/boundary.py`, `app/tools/boundary_visualization/`)
1. Đọc coordinates từ `mat.area_polygon` (raw SQL, không phải ORM)
2. Parse nested GeoJSON-like coordinate arrays
3. Tạo Folium map với polygon layers
4. Lưu HTML file vào `ui/pages/boundary_map_{id}.html`

#### Output
- Interactive Folium HTML map
- `GET /pages/boundary_map_{id}.html` — serve file

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `mat` | `area_polygon` | Geometry polygon data (raw SQL access) |

---

### F9. EXPLORER QUEUE — DUYỆT HÀNG ĐỢI XỬ LÝ

**Trạng thái:** ✅ Hoàn chỉnh

#### Input
- `GET /api/explorer/queue?page=1&limit=50&status=PENDING`
- `GET /api/parser/sample` — random sample 1 record

#### Process
- SQLAlchemy query `prq.address_cleansing_queue` với filter + pagination
- Trả về list records kèm AI results

#### Output
```json
{
  "total": 15420,
  "items": [
    {
      "id": 1001,
      "raw_address": "90 Ly Thuong Kiet Q.TB HCM",
      "processing_status": "COMPLETED",
      "address_standardized": "90 Lý Thường Kiệt, Phường 12, Tân Bình, TPHCM",
      "selected_ai_model": "MGTE",
      "phobert_confidence_score": 0.8720,
      "mgte_confidence_score": 0.9130
    }
  ]
}
```

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `prq` | `address_cleansing_queue` | Source data |

---

### F10. GIAO DIỆN WEB (Web UI — 15+ trang)

**Trạng thái:** ✅ Tốt

| Trang | Endpoint | Chức năng |
|-------|----------|-----------|
| `overview.html` | `/overview.html` | Dashboard tổng quan KPIs |
| `training.html` | `/training.html` | Lịch sử training, accuracy chart |
| `experiments.html` | `/experiments.html` | Benchmark model comparison |
| `parser.html` | `/parser.html` | Real-time address parser |
| `explorer.html` | `/explorer.html` | Duyệt queue xử lý |
| `batch.html` | `/batch.html` | Trigger & monitor batch jobs |
| `lookup.html` | `/lookup.html` | Tra cứu mapping đơn vị |
| `admin-units.html` | `/admin-units.html` | Quản lý hành chính |
| `ward-mapper.html` | `/ward-mapper.html` | Tool ánh xạ phường/xã |
| `nso-sync.html` | `/nso-sync.html` | Quản lý đồng bộ NSO |
| `osm-enrichment.html` | `/osm-enrichment.html` | OSM data management |
| `boundary-visualization.html` | `/boundary-visualization.html` | Polygon map viewer |
| `evidence.html` | `/evidence.html` | Experiment artifacts |
| `label-studio.html` | `/label-studio.html` | Annotation interface |
| `settings.html` | `/settings.html` | Cấu hình hệ thống |

---

### F11. TỰ ĐỘNG SINH DỮ LIỆU HUẤN LUYỆN (Synthetic Data Generation)

**Trạng thái:** ✅ Cơ bản

#### Input
- CLI: `python app/main.py data:generate --count 10000`

#### Process (`app/services/synthetic_mixer.py`)
1. Random chọn province/district/ward từ `mat.*`
2. Áp dụng noise patterns: bỏ dấu, viết tắt, đảo thứ tự, typo
3. Tạo chuỗi địa chỉ + BIO tags tương ứng
4. Optional: dùng Qwen3 để generate câu phức tạp hơn

#### Output
- JSONL file với format `{"text": "...", "tags": [...]}`
- Lưu vào `ath.training_datasets`

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `ath` | `training_datasets` | Lưu raw_text + ner_tags_json |
| `mat` | `province/district/ward` | Source để sample đơn vị hành chính |

---

### F12. LOOKUP MAPPING ĐỊA CHỈ CŨ → MỚI

**Trạng thái:** ✅ Cơ bản

#### Input
- `GET /api/lookup/mapping?ward_name=Phường+12&district_name=Tân+Bình`

#### Process
- Query `mat.ward_mapping` để tìm ánh xạ
- Kết hợp với `mat.ward` để lấy tên đơn vị mới

#### Output
```json
{
  "old": {"ward_id": 770001, "ward_name": "Phường 12", "district": "Tân Bình"},
  "new": {"ward_id": 800001, "ward_name": "Phường Tân Bình", "province": "TPHCM"},
  "effective_date": "2025-07-01",
  "relationship_type": "MERGES_INTO"
}
```

#### Tables liên quan
| Schema | Bảng | Vai trò |
|--------|------|---------|
| `mat` | `ward_mapping` | Ánh xạ old_id → new_id |
| `mat` | `ward/district/province` | Tên đơn vị hành chính |

---

## 3. PHẦN II — TÍNH NĂNG CHƯA ĐÁP ỨNG

---

### G1. n8n GOV-SYNC — NÂNG CẤP SCD TYPE 2 & ALERT ⚡ ƯU TIÊN CAO

**Mô tả luận văn:** Workflow n8n tự động: Trigger → SOAP/REST Gov API → XML/JSON Parser → SCD Type 2 → PostgreSQL → Typesense Upsert → Alert

**Hiện trạng (đã có):** n8n Browserless crawler đang chạy cron 01:00 AM, scrape `danhmuchanhchinh.nso.gov.vn`, UPDATE `mat.ward` theo `ward_no` + `admin_version=2`

**Phần còn thiếu:** SCD Type 2 history tracking, Typesense upsert sau sync, Alert notification, persist sync_log

#### Kế hoạch thực hiện (chỉ bổ sung phần còn thiếu)

**Bước 1: Tạo SCD Type 2 tables còn thiếu (Ngày 1)**

```sql
-- Thêm cột SCD Type 2 vào mat.province (migration)
ALTER TABLE mat.province 
  ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS valid_to TIMESTAMPTZ DEFAULT '9999-12-31',
  ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS version_id INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS predecessor_id INTEGER REFERENCES mat.province(row_id);

-- Bảng đồ thị quan hệ hành chính (chưa có trong codebase)
CREATE TABLE mat.unit_edge (
  id SERIAL PRIMARY KEY,
  from_unit_id INTEGER NOT NULL,
  from_level VARCHAR(20) NOT NULL,  -- 'province','district','ward'
  to_unit_id INTEGER NOT NULL,
  to_level VARCHAR(20) NOT NULL,
  relationship_type VARCHAR(50) NOT NULL, -- MERGES_INTO, SPLIT_FROM, RENAMES_TO, BOUNDARY_ADJUSTED
  effective_date TIMESTAMPTZ NOT NULL,
  resolution_ref VARCHAR(200),  -- Số nghị quyết
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng sync log (persist)
CREATE TABLE ath.sync_log (
  id SERIAL PRIMARY KEY,
  sync_source VARCHAR(50),  -- 'NSO_API', 'N8N_WORKFLOW', 'MANUAL'
  level VARCHAR(20),
  unit_id INTEGER,
  change_type VARCHAR(30),  -- 'CREATE','UPDATE','MERGE','RENAME'
  old_value JSONB,
  new_value JSONB,
  synced_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Bước 3: Implement SCD Type 2 logic trong Python (Ngày 4-5)**

```python
# app/services/scd_sync.py — NEW FILE
def scd_upsert_unit(session, level: str, unit_data: dict, effective_date: datetime):
    """
    Thực hiện SCD Type 2 upsert cho một đơn vị hành chính.
    Logic:
    1. Tìm bản ghi is_current=True theo unit_id
    2. Nếu có thay đổi: đóng bản ghi cũ (valid_to=now, is_current=False)
    3. Tạo bản ghi mới với valid_from=now, is_current=True, version_id+1
    4. Ghi log vào ath.sync_log
    """
    model_map = {'province': Province, 'district': District, 'ward': Ward}
    Model = model_map[level]
    id_field = f"{level}_id"
    
    existing = session.query(Model).filter(
        getattr(Model, id_field) == unit_data[id_field],
        Model.is_current == True
    ).first()
    
    if existing:
        # Tính checksum để phát hiện thay đổi thực sự
        checksum_old = compute_checksum(existing)
        checksum_new = compute_checksum(unit_data)
        if checksum_old == checksum_new:
            return  # Không thay đổi, bỏ qua
        
        # Đóng bản ghi cũ
        existing.valid_to = effective_date
        existing.is_current = False
    
    # Tạo bản ghi mới
    new_record = Model(
        **unit_data,
        valid_from=effective_date,
        valid_to=datetime(9999, 12, 31),
        is_current=True,
        version_id=(existing.version_id + 1 if existing else 1),
        predecessor_id=(existing.row_id if existing else None)
    )
    session.add(new_record)
```

**Bước 4: Nâng cấp n8n workflow hiện có (Ngày 6-8)**

> **File hiện tại:** `docs/n8n/Automated Geospatial Data Extraction and Synchronization System.json`  
> **Workflow ID:** `S5smdRYjLEmaaMKp` | **Active:** `true`

Workflow hiện có các nodes sau (đã hoạt động):
```
[Schedule Trigger: 01:00 AM]  +  [Manual Trigger]
            ↓
[Global Parameter Configuration]  ← Cấu hình browserlessUrl, token, filePath
            ↓
[Cache/Storage Sanitization]  ← Xóa /home/node/.n8n/danhmuc_hanhchinh.json
            ↓
[Index Range Generation]  ← Tạo 34 items (index 0→33)
            ↓
[Iteration Controller]  ← SplitInBatches loop
            ↓
[Web Scraper / Data Extraction Service]  ← Browserless POST /function
   (scrape danhmuchanhchinh.nso.gov.vn: ma, ten, tenAnh, cap,
    ngayQuyetDinh, ngayHieuLuc, danSo, dienTich, ghiChu)
            ↓
[Data Normalization & Transformation]  ← Append vào JSON file tạm
            ↓
[Relational Database Persistence]  ← UPDATE mat.ward
   WHERE ward_no = :ma AND admin_version = 2
            ↓
[loop back → Iteration Controller]
```

Cần **thêm vào workflow hiện có** (không tạo mới):
```
Sau [Relational Database Persistence]:
  → [IF: is last batch?]
      → YES: [Sync Log Insert] → ath.sync_log
             [Notification Node] → Email/Slack alert
      → NO:  loop back → [Iteration Controller]
```

**Bước 5: API lịch sử đơn vị (Ngày 9-10)**

```python
# Thêm vào app/api/server.py
@api_router.get("/admin-unit/{level}/{unit_id}/history")
def get_unit_history(level: str, unit_id: int, at: Optional[date] = None, db=Depends(get_db)):
    """
    Trả về trạng thái đơn vị hành chính tại thời điểm `at`.
    GET /api/admin-unit/ward/770001/history?at=2024-01-01
    """
    Model = {'province': Province, 'district': District, 'ward': Ward}[level]
    id_field = f"{level}_id"
    
    if at:
        record = db.query(Model).filter(
            getattr(Model, id_field) == unit_id,
            Model.valid_from <= at,
            Model.valid_to > at
        ).first()
    else:
        records = db.query(Model).filter(
            getattr(Model, id_field) == unit_id
        ).order_by(Model.version_id).all()
    
    return {"history": records}
```

**Deliverables:**
- [ ] `docker-compose.yml` cập nhật với n8n service
- [ ] Migration SQL thêm cột SCD Type 2 vào `mat.*`
- [ ] `mat.unit_edge` table mới
- [ ] `ath.sync_log` table mới
- [ ] `app/services/scd_sync.py` — SCD Type 2 logic
- [ ] `docs/n8n/gov_sync_workflow.json` — workflow export
- [ ] `GET /api/admin-unit/{level}/{id}/history` endpoint

---

### G2. ADDRESS CONFIDENCE SCORE (ACS) ĐẦY ĐỦ ⚡ ƯU TIÊN CAO

**Mô tả luận văn:** 
```
ACS(ai|q) = α·S_text(q,ai) + β·S_sem(q,ai) + γ·V_hierarchy(ai) + δ·V_temporal(ai)
```
Bảng quyết định: ≥0.9 → Auto-Accept | 0.7-0.9 → Auto-Convert | 0.5-0.7 → Suggest | <0.5 → Reject

**Hiện trạng:** Chỉ có `phobert_confidence_score` và `mgte_confidence_score` đơn giản (single model), chưa có công thức tổng hợp 4 thành phần

#### Kế hoạch thực hiện

**Bước 1: Implement ACS calculator (Ngày 1-3)**

```python
# app/ai/acs_calculator.py — NEW FILE
from dataclasses import dataclass
from typing import Optional
import math

@dataclass
class ACSComponents:
    s_text: float      # Typesense full-text score [0-1]
    s_sem: float       # Cosine similarity embedding [0-1]  
    v_hierarchy: float # Hierarchy validation [0-1]
    v_temporal: float  # Temporal weight [0-1]

class ACSCalculator:
    """
    Address Confidence Score theo công thức luận văn:
    ACS = α·S_text + β·S_sem + γ·V_hierarchy + δ·V_temporal
    Default weights: α=0.25, β=0.40, γ=0.25, δ=0.10
    """
    
    def __init__(self, alpha=0.25, beta=0.40, gamma=0.25, delta=0.10):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
    
    def compute(self, components: ACSComponents) -> float:
        return (
            self.alpha * components.s_text +
            self.beta  * components.s_sem +
            self.gamma * components.v_hierarchy +
            self.delta * components.v_temporal
        )
    
    def validate_hierarchy(self, ward_id: int, district_id: int, province_id: int, db) -> float:
        """Kiểm tra Phường ∈ Huyện ∈ Tỉnh trong mat.*"""
        ward = db.query(Ward).filter(Ward.ward_id == ward_id).first()
        if not ward: return 0.0
        if ward.district_id != district_id: return 0.3
        district = db.query(District).filter(District.district_id == district_id).first()
        if not district: return 0.5
        if district.province_id != province_id: return 0.5
        return 1.0
    
    def compute_temporal_weight(self, address_version: str, current_version: str) -> float:
        """Phạt nhẹ địa chỉ hành chính cũ nhưng không loại bỏ"""
        if address_version == current_version:
            return 1.0
        return 0.75  # Phạt 25% nếu địa chỉ thuộc version cũ
    
    def get_decision(self, acs: float) -> dict:
        if acs >= 0.9:
            return {"action": "AUTO_ACCEPT", "message": "Địa chỉ chính xác hoàn toàn"}
        elif acs >= 0.7:
            return {"action": "AUTO_CONVERT", "message": "Đã cập nhật sang đơn vị hành chính mới 2025"}
        elif acs >= 0.5:
            return {"action": "SUGGEST", "message": "Có phải bạn muốn tìm...?"}
        else:
            return {"action": "REJECT", "message": "Không tìm thấy địa chỉ hợp lệ"}
```

**Bước 2: Tích hợp ACS vào production pipeline (Ngày 4-5)**
- Cập nhật `app/ai/production_pipeline.py` gọi `ACSCalculator.compute()`
- Thêm cột `acs_score NUMERIC(5,4)` và `acs_decision VARCHAR(20)` vào `prq.address_cleansing_queue`
- Thêm cột `s_text NUMERIC(5,4)`, `s_sem NUMERIC(5,4)`, `v_hierarchy NUMERIC(5,4)`, `v_temporal NUMERIC(5,4)` để debug

**Bước 3: Expose ACS trong Parser API (Ngày 6)**
- Cập nhật response của `POST /api/parser/analyze` để bao gồm `acs_score` và `acs_decision`

**Deliverables:**
- [ ] `app/ai/acs_calculator.py` — ACS module
- [ ] Migration thêm cột `acs_score`, `acs_decision`, `acs_components` vào `prq.address_cleansing_queue`
- [ ] Tích hợp ACS vào `production_pipeline.py`
- [ ] API response cập nhật với ACS

---

### G3. GEOSPATIAL API — POINT-IN-POLYGON ⚡ ƯU TIÊN CAO

**Mô tả luận văn:** 
```sql
SELECT ward_id FROM mat.area_polygon 
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(lng, lat), 4326))
```
API: `POST /api/spatial/subdivide` nhận batch tọa độ → trả về đơn vị hành chính

**Hiện trạng:** Chỉ có boundary visualization (Folium HTML), không có API Point-in-Polygon

#### Kế hoạch thực hiện

**Bước 1: Đảm bảo PostGIS và `mat.area_polygon` đúng schema (Ngày 1-2)**

```sql
-- Kiểm tra và tạo bảng nếu chưa có đúng cấu trúc
CREATE TABLE IF NOT EXISTS mat.area_polygon (
  id SERIAL PRIMARY KEY,
  ward_id INTEGER REFERENCES mat.ward(ward_id),
  district_id INTEGER,
  province_id INTEGER,
  level VARCHAR(20) NOT NULL,  -- 'ward', 'district', 'province'
  geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
  source VARCHAR(50),  -- 'GSO', 'OSM', 'MANUAL'
  valid_from DATE,
  valid_to DATE,
  is_current BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index (bắt buộc cho hiệu năng)
CREATE INDEX IF NOT EXISTS idx_area_polygon_geom 
  ON mat.area_polygon USING GIST(geom);

CREATE INDEX IF NOT EXISTS idx_area_polygon_ward_current 
  ON mat.area_polygon(ward_id, is_current) WHERE is_current = TRUE;
```

**Bước 2: Implement Spatial API (Ngày 3-5)**

```python
# app/api/spatial.py — NEW FILE
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text

spatial_router = APIRouter(prefix="/spatial", tags=["spatial"])

class CoordinateInput(BaseModel):
    lat: float
    lng: float
    reference_id: Optional[str] = None  # để client track kết quả

class SubdivideRequest(BaseModel):
    coordinates: List[CoordinateInput]

@spatial_router.post("/subdivide")
def subdivide_batch(request: SubdivideRequest, db=Depends(get_db)):
    """
    Point-in-Polygon: nhận batch tọa độ → trả về đơn vị hành chính.
    Fallback: nếu ST_Contains không có kết quả → dùng ST_Distance nearest.
    """
    results = []
    for coord in request.coordinates:
        # Thử ST_Contains trước
        sql = text("""
            SELECT 
                ap.ward_id, w.ward_name,
                w.district_id, d.district_name,
                w.province_id, p.province_name,
                ST_AsGeoJSON(ap.geom)::jsonb as geometry
            FROM mat.area_polygon ap
            JOIN mat.ward w ON w.ward_id = ap.ward_id
            JOIN mat.district d ON d.district_id = w.district_id  
            JOIN mat.province p ON p.province_id = w.province_id
            WHERE ap.level = 'ward'
              AND ap.is_current = TRUE
              AND ST_Contains(ap.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            LIMIT 1
        """)
        row = db.execute(sql, {"lat": coord.lat, "lng": coord.lng}).fetchone()
        
        if not row:
            # Fallback: ST_Distance nearest neighbor
            sql_fallback = text("""
                SELECT ap.ward_id, w.ward_name, 
                       w.district_id, d.district_name,
                       w.province_id, p.province_name,
                       ST_Distance(
                           ap.geom::geography, 
                           ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                       ) as dist_meters
                FROM mat.area_polygon ap
                JOIN mat.ward w ON w.ward_id = ap.ward_id
                JOIN mat.district d ON d.district_id = w.district_id
                JOIN mat.province p ON p.province_id = w.province_id
                WHERE ap.level = 'ward' AND ap.is_current = TRUE
                ORDER BY ap.geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                LIMIT 1
            """)
            row = db.execute(sql_fallback, {"lat": coord.lat, "lng": coord.lng}).fetchone()
            match_type = "NEAREST_NEIGHBOR"
        else:
            match_type = "CONTAINS"
        
        results.append({
            "reference_id": coord.reference_id,
            "lat": coord.lat, "lng": coord.lng,
            "match_type": match_type,
            "ward_id": row.ward_id if row else None,
            "ward_name": row.ward_name if row else None,
            "district_id": row.district_id if row else None,
            "district_name": row.district_name if row else None,
            "province_id": row.province_id if row else None,
            "province_name": row.province_name if row else None,
        })
    
    return {"count": len(results), "results": results}
```

**Bước 3: Implement 3 chiến lược hiệu chỉnh polygon (Ngày 6-10)**

```python
# app/geometry/buffer_union.py — NEW FILE
import shapely.geometry as sg
from shapely.ops import unary_union

def buffer_union_correction(polygon_wkt: str, outlier_points: list, buffer_meters: float = 50) -> str:
    """
    Chiến lược 1: Mở rộng polygon bằng buffer quanh điểm ngoại vi.
    Phù hợp: điểm nằm sát biên, sai số nhỏ (<50m).
    """
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)
    
    polygon = sg.from_wkt(polygon_wkt)
    polygon_metric = sg.transform(transformer.transform, polygon)
    
    buffers = []
    for lat, lng in outlier_points:
        x, y = transformer.transform(lng, lat)
        point = sg.Point(x, y)
        buffers.append(point.buffer(buffer_meters))
    
    expanded = unary_union([polygon_metric] + buffers)
    return expanded.wkt

# app/geometry/concave_hull.py — NEW FILE  
def concave_hull_correction(delivery_points: list, alpha: float = 0.5) -> str:
    """
    Chiến lược 2: Tính lại polygon từ đám mây điểm giao nhận thực tế.
    Phù hợp: polygon lưu trữ quá lỗi thời, nhiều điểm nằm ngoài.
    Yêu cầu: ít nhất 10 điểm để kết quả đáng tin cậy.
    """
    from scipy.spatial import Delaunay
    import numpy as np
    # Alpha Shape algorithm implementation
    ...

# app/geometry/edge_inject.py — NEW FILE
def edge_inject_correction(polygon_wkt: str, outlier_point: tuple) -> str:
    """
    Chiến lược 3: Chèn điểm ngoại vi vào cạnh gần nhất (vi phẫu thuật).
    Phù hợp: chỉ 1-2 điểm bất thường, ít xâm invasive nhất.
    """
    ...
```

**Bước 4: Mismatch Analysis Pipeline (Ngày 11-13)**

```python
# app/services/spatial_mismatch.py — NEW FILE
import pandas as pd

def analyze_csv_mismatch(csv_path: str, output_html: str = None) -> dict:
    """
    Quy trình đối soát từ CSV đơn hàng:
    1. Đọc CSV (cột: lat, lng, ward_id, district_id, province_id)
    2. Batch call /api/spatial/subdivide
    3. So sánh kết quả vs nhãn gốc
    4. Sinh báo cáo mismatch
    5. Optional: Folium visualization
    """
    df = pd.read_csv(csv_path)
    
    # Batch subdivide
    coords = [{"lat": r.lat, "lng": r.lng, "reference_id": str(i)} 
              for i, r in df.iterrows()]
    
    # ... so sánh và tạo báo cáo
    report = {
        "total": len(df),
        "province_match_rate": ...,
        "district_match_rate": ...,
        "ward_match_rate": ...,
        "mismatch_details": [...]
    }
    return report
```

**Deliverables:**
- [ ] `app/api/spatial.py` — Spatial API router
- [ ] `POST /api/spatial/subdivide` endpoint
- [ ] `GET /api/spatial/mismatch-report` endpoint
- [ ] `app/geometry/buffer_union.py` 
- [ ] `app/geometry/concave_hull.py`
- [ ] `app/geometry/edge_inject.py`
- [ ] `app/services/spatial_mismatch.py`
- [ ] `mat.area_polygon` ORM model trong `database.py`
- [ ] Spatial index SQL migration

---

### G4. WATERFALL ENRICHMENT (Đa nguồn: Redis→OSM→Google) ⚡ ƯU TIÊN TRUNG BÌNH

**Mô tả luận văn:** 
- Lớp 1: Redis cache (hit rate 20-40%)
- Lớp 2: OSM + VietMap (cover 40-50%)
- Lớp 3: Google Maps (< 10-20% request)
- Xử lý geocoding quality: ROOFTOP → RANGE_INTERPOLATED → GEOMETRIC_CENTER → APPROXIMATE

**Hiện trạng:** OSM fetcher có, nhưng chưa có Redis layer, chưa có Waterfall logic, chưa có Google Geocoding integration

#### Kế hoạch thực hiện

**Bước 1: Thêm Redis vào stack (Ngày 1)**

```yaml
# docker-compose.yml — thêm Redis
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

```python
# app/core/config.py — thêm Redis config
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
REDIS_TTL_SECONDS: int = int(os.getenv("REDIS_TTL", 86400))  # 24h default
```

**Bước 2: Implement Waterfall Enrichment Service (Ngày 2-6)**

```python
# app/services/waterfall_enrichment.py — NEW FILE
import redis
import json
import hashlib

class WaterfallEnrichmentService:
    """
    Kiến trúc Waterfall Enrichment:
    L1: Redis Cache (chi phí = 0, hit rate ~30%)
    L2: OSM Overpass (chi phí thấp)  
    L3: VietMap API (chi phí thấp, server VN)
    L4: Google Maps (chỉ khi L1+L2+L3 thất bại hoặc confidence thấp)
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=Config.REDIS_HOST, 
            port=Config.REDIS_PORT
        )
    
    def _cache_key(self, address: str) -> str:
        return f"vnai:enrich:{hashlib.md5(address.encode()).hexdigest()}"
    
    async def enrich(self, standardized_address: dict) -> dict:
        address_str = standardized_address.get("address_standardized", "")
        cache_key = self._cache_key(address_str)
        
        # L1: Redis Cache
        cached = self.redis_client.get(cache_key)
        if cached:
            return {"result": json.loads(cached), "source": "CACHE", "cost": 0}
        
        # L2: OSM Lookup (internal DB)
        osm_result = await self._lookup_osm(standardized_address)
        if osm_result and osm_result.get("confidence", 0) > 0.7:
            self.redis_client.setex(cache_key, Config.REDIS_TTL_SECONDS, json.dumps(osm_result))
            return {"result": osm_result, "source": "OSM", "cost": 0}
        
        # L3: VietMap API
        vietmap_result = await self._call_vietmap(address_str)
        if vietmap_result:
            self.redis_client.setex(cache_key, Config.REDIS_TTL_SECONDS, json.dumps(vietmap_result))
            return {"result": vietmap_result, "source": "VIETMAP", "cost": 0.001}
        
        # L4: Google Maps (fallback)
        google_result = await self._call_google_geocoding(address_str)
        quality = google_result.get("location_type", "APPROXIMATE")
        result = {**google_result, "geocoding_quality": quality}
        self.redis_client.setex(cache_key, Config.REDIS_TTL_SECONDS, json.dumps(result))
        return {"result": result, "source": "GOOGLE", "cost": 0.005}
    
    async def _call_google_geocoding(self, address: str) -> dict:
        """Gọi Google Maps Geocoding API"""
        # ROOFTOP / RANGE_INTERPOLATED / GEOMETRIC_CENTER / APPROXIMATE
        ...
    
    async def _lookup_osm(self, address: dict) -> dict:
        """Tìm trong osm.streets, osm.pois theo tên đường + phường"""
        ...
    
    async def _call_vietmap(self, address: str) -> dict:
        """VietMap Migration API để xử lý địa chỉ cũ → mới"""
        ...
```

**Bước 3: Thêm endpoint enrichment (Ngày 7)**

```python
@api_router.post("/enrich")
async def enrich_address(body: dict, db=Depends(get_db)):
    """
    POST /api/enrich
    Input: {"address_id": 1001} hoặc {"raw_address": "..."}
    Output: enriched address với lat/lng, polygon, geocoding_quality
    """
    ...
```

**Bước 4: Thêm metrics theo dõi hit rate (Ngày 8)**

```sql
-- Bảng theo dõi enrichment metrics
CREATE TABLE ath.enrichment_metrics (
  id SERIAL PRIMARY KEY,
  source VARCHAR(20) NOT NULL,  -- CACHE, OSM, VIETMAP, GOOGLE
  count INTEGER DEFAULT 0,
  date DATE DEFAULT CURRENT_DATE,
  UNIQUE (source, date)
);
```

**Deliverables:**
- [ ] `docker-compose.yml` với Redis service
- [ ] `app/services/waterfall_enrichment.py`
- [ ] `POST /api/enrich` endpoint
- [ ] `ath.enrichment_metrics` table
- [ ] `GET /api/enrichment/summary` cập nhật với hit rate per source
- [ ] Google Maps Geocoding API integration
- [ ] VietMap API integration

---

### G5. TEMPORAL-AWARE ADDRESS — XỬ LÝ ĐỊA CHỈ LƯỠNG THỜI ⚡ ƯU TIÊN CAO

**Mô tả luận văn:** Hệ thống phải hiểu đồng thời địa chỉ Pre-2025 và Post-2025 (Dual-Epoch Recognition). SCD Temporal Lookup: kiểm tra `valid_from`, `valid_to` để trả về kết quả phù hợp với thời điểm địa chỉ.

**Hiện trạng:** `mat.ward_mapping` có các cột `effective_date_from/to` nhưng pipeline AI không sử dụng temporal lookup. Không có logic phát hiện epoch của địa chỉ đầu vào.

#### Kế hoạch thực hiện

**Bước 1: Epoch Detector (Ngày 1-2)**

```python
# app/ai/epoch_detector.py — NEW FILE
import re
from datetime import date

REFORM_DATE = date(2025, 7, 1)

# Keywords chỉ xuất hiện trong Pre-2025
PRE_2025_KEYWORDS = {
    "quận", "huyện", "thị xã",
    # Tên đơn vị cụ thể đã bị bãi bỏ
}

# Tên đơn vị Post-2025 (load từ mat.ward với admin_version=2)
POST_2025_UNIT_NAMES = set()  # populated from DB

def detect_address_epoch(address: str, db) -> str:
    """
    Phát hiện địa chỉ thuộc Pre-2025 hay Post-2025.
    Returns: 'PRE_2025' | 'POST_2025' | 'AMBIGUOUS'
    """
    address_lower = address.lower()
    
    # Dấu hiệu Pre-2025: có từ "quận", "huyện" (đã bãi bỏ)
    pre_signals = sum(1 for kw in PRE_2025_KEYWORDS if kw in address_lower)
    
    # Dấu hiệu Post-2025: khớp với tên đơn vị mới (admin_version=2)
    post_signals = sum(1 for name in POST_2025_UNIT_NAMES if name.lower() in address_lower)
    
    if pre_signals > 0 and post_signals == 0:
        return "PRE_2025"
    elif post_signals > 0 and pre_signals == 0:
        return "POST_2025"
    else:
        return "AMBIGUOUS"
```

**Bước 2: Tích hợp vào Siamese Matching với temporal filter (Ngày 3-4)**

```python
# Cập nhật app/ai/models/siamese_mgte.py
def match_with_temporal(self, query: str, epoch: str, db) -> dict:
    """
    Khớp với corpus có temporal filter:
    - Pre-2025: ưu tiên mat.ward với admin_version=1
    - Post-2025: ưu tiên mat.ward với admin_version=2  
    - Ambiguous: search cả 2, merge kết quả với temporal penalty
    """
    if epoch == "PRE_2025":
        corpus = self.build_corpus(db, admin_version=1)
    elif epoch == "POST_2025":
        corpus = self.build_corpus(db, admin_version=2)
    else:
        corpus_v1 = self.build_corpus(db, admin_version=1)
        corpus_v2 = self.build_corpus(db, admin_version=2)
        corpus = corpus_v1 + corpus_v2
    
    return self.match(query, corpus)
```

**Bước 3: Migration API (old address → new) (Ngày 5-6)**

```python
@api_router.post("/migrate-address")
def migrate_address(body: dict, db=Depends(get_db)):
    """
    POST /api/migrate-address
    Input: {"address": "123 Lê Văn Duyệt, Q.Bình Thạnh, HCM"}
    Output: địa chỉ chuẩn Post-2025 + mapping path
    """
    # 1. Detect epoch
    # 2. NER + Siamese matching (Pre-2025 corpus)  
    # 3. Lookup mat.ward_mapping → old_ward_id → new_ward_id
    # 4. Compose new address với tên đơn vị Post-2025
    # 5. Trả về cả địa chỉ cũ, mới, và path ánh xạ
    ...
```

**Deliverables:**
- [ ] `app/ai/epoch_detector.py`
- [ ] Cập nhật `siamese_mgte.py` với temporal corpus filter
- [ ] Cập nhật `production_pipeline.py` dùng epoch detector
- [ ] `POST /api/migrate-address` endpoint
- [ ] Thêm `address_epoch VARCHAR(20)` vào `prq.address_cleansing_queue`

---

### G6. FAISS VECTOR INDEX CHO SIAMESE MATCHING ⚡ ƯU TIÊN TRUNG BÌNH

**Mô tả luận văn:** FAISS IVFHNSW cho Approximate Nearest Neighbor search, xây dựng embedding index cho toàn bộ `mat.ward`, `mat.district`, `mat.province`

**Hiện trạng:** mGTE model có nhưng không dùng FAISS, dùng brute-force cosine search

#### Kế hoạch thực hiện

**Bước 1: Cài đặt FAISS (Ngày 1)**
```bash
pip install faiss-cpu  # hoặc faiss-gpu nếu có GPU
```

**Bước 2: Implement FAISS Index Manager (Ngày 2-4)**

```python
# app/ai/faiss_index.py — NEW FILE
import faiss
import numpy as np
import pickle
from pathlib import Path

class AdminUnitFAISSIndex:
    """
    FAISS IVFHNSW index cho admin units embedding lookup.
    Index được build 1 lần và load lại khi restart.
    """
    INDEX_PATH = Path("data/faiss_admin_units.index")
    META_PATH = Path("data/faiss_admin_units_meta.pkl")
    
    def build_index(self, model, db, force_rebuild=False):
        if self.INDEX_PATH.exists() and not force_rebuild:
            return self.load_index()
        
        # Lấy tất cả đơn vị hành chính
        wards = db.query(Ward).filter(Ward.is_current == True).all()
        texts = [f"{w.ward_name} {w.district_name} {w.province_name}" for w in wards]
        ids = [w.ward_id for w in wards]
        
        # Encode bằng mGTE
        embeddings = model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings)
        
        # Build IVFHNSW index
        dim = embeddings.shape[1]
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, min(100, len(texts)//10))
        index.train(embeddings)
        index.add(embeddings)
        
        # Lưu index + metadata
        faiss.write_index(index, str(self.INDEX_PATH))
        with open(self.META_PATH, 'wb') as f:
            pickle.dump({"ids": ids, "texts": texts}, f)
        
        return index, ids
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list:
        index = faiss.read_index(str(self.INDEX_PATH))
        with open(self.META_PATH, 'rb') as f:
            meta = pickle.load(f)
        
        query = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query)
        scores, indices = index.search(query, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                results.append({
                    "ward_id": meta["ids"][idx],
                    "text": meta["texts"][idx],
                    "similarity": float(score)
                })
        return results
```

**Bước 3: API rebuild index (Ngày 5)**

```python
@api_router.post("/admin/rebuild-index")
def rebuild_faiss_index(db=Depends(get_db)):
    """Trigger rebuild FAISS index (chạy background)"""
    ...
```

**Deliverables:**
- [ ] `app/ai/faiss_index.py`
- [ ] Tích hợp FAISS vào `siamese_mgte.py`
- [ ] `POST /api/admin/rebuild-index` endpoint
- [ ] CLI: `python app/main.py admin:rebuild-index`

---

### G7. TRAINING PIPELINE PhoBERT NER THỰC SỰ ⚡ ƯU TIÊN TRUNG BÌNH

**Mô tả luận văn:** Fine-tune PhoBERT-base + BiLSTM-CRF với 100,000+ mẫu, BIO tags, VnCoreNLP tokenizer, FastBPE

**Hiện trạng:** `app/ai/train_ner.py` có code nhưng chưa có dữ liệu huấn luyện thực tế, chưa có BiLSTM-CRF layer

#### Kế hoạch thực hiện

**Bước 1: Chuẩn bị dữ liệu từ Label Studio (Ngày 1-3)**
- Export annotation từ Label Studio (đã tích hợp)
- Convert format → BIO tags
- Split 80/10/10 (train/dev/test)
- Lưu vào `ath.training_datasets`

**Bước 2: Fine-tune PhoBERT với BiLSTM-CRF (Ngày 4-7)**

```python
# app/ai/models/ner_bilstm_crf.py — NEW FILE
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn as nn
from torchcrf import CRF

class PhoBERTBiLSTMCRF(nn.Module):
    """
    Kiến trúc: PhoBERT-base → BiLSTM → CRF
    Labels: B/I-HOUSENUM, B/I-ALLEY, B/I-STREET, B/I-WARD, 
            B/I-DISTRICT, B/I-PROVINCE, B/I-POI, O
    """
    LABELS = [
        "O",
        "B-HOUSENUM", "I-HOUSENUM",
        "B-ALLEY", "I-ALLEY",
        "B-STREET", "I-STREET",
        "B-WARD", "I-WARD",
        "B-DISTRICT", "I-DISTRICT",
        "B-PROVINCE", "I-PROVINCE",
        "B-POI", "I-POI"
    ]
    
    def __init__(self, dropout=0.1, lstm_hidden=256):
        super().__init__()
        self.bert = AutoModel.from_pretrained("vinai/phobert-base")
        bert_dim = self.bert.config.hidden_size  # 768
        
        self.lstm = nn.LSTM(
            bert_dim, lstm_hidden, 
            bidirectional=True, batch_first=True
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(lstm_hidden * 2, len(self.LABELS))
        self.crf = CRF(len(self.LABELS), batch_first=True)
    
    def forward(self, input_ids, attention_mask, labels=None):
        bert_out = self.bert(input_ids, attention_mask).last_hidden_state
        lstm_out, _ = self.lstm(self.dropout(bert_out))
        emissions = self.fc(self.dropout(lstm_out))
        
        if labels is not None:
            loss = -self.crf(emissions, labels, mask=attention_mask.bool())
            return loss
        else:
            return self.crf.decode(emissions, mask=attention_mask.bool())
```

**Deliverables:**
- [ ] `app/ai/models/ner_bilstm_crf.py` — model architecture
- [ ] Cập nhật `app/ai/train_ner.py` dùng model mới
- [ ] Script augmentation data (viết tắt, không dấu, hoán đổi thứ tự)
- [ ] Script export annotation từ Label Studio → BIO format

---

### G8. BENCHMARK BỘ DỮ LIỆU CHUẨN D1-D5 ⚡ ƯU TIÊN TRUNG BÌNH

**Mô tả luận văn:** 
- D1: 2,000 mẫu đô thị chuẩn
- D2: 1,000 mẫu nhiễu cao (lỗi chính tả, không dấu)
- D3: 1,000 mẫu Pre-2025 (địa danh cũ)
- D4: 1,000 mẫu nông thôn (thiếu số nhà)
- D5: 1,000 mẫu ranh giới (tọa độ biên)

**Hiện trạng:** Chưa có bộ test chuẩn, experiment runner chạy trên dữ liệu tuỳ ý

#### Kế hoạch thực hiện

**Bước 1: Tạo benchmark dataset schema (Ngày 1-2)**

```sql
-- Bảng lưu benchmark datasets chuẩn
CREATE TABLE ath.benchmark_dataset (
  id SERIAL PRIMARY KEY,
  dataset_code VARCHAR(10) NOT NULL,  -- D1, D2, D3, D4, D5
  raw_address TEXT NOT NULL,
  ground_truth_province_id INTEGER,
  ground_truth_district_id INTEGER,
  ground_truth_ward_id INTEGER,
  ground_truth_street TEXT,
  ground_truth_house_number TEXT,
  address_epoch VARCHAR(20),  -- PRE_2025, POST_2025
  noise_type VARCHAR(50),     -- TYPO, NO_DIACRITICS, ABBREVIATION, MISSING_LEVEL
  lat NUMERIC(10,7),
  lng NUMERIC(10,7),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Kết quả benchmark theo từng run
CREATE TABLE ath.benchmark_run_result (
  id SERIAL PRIMARY KEY,
  run_id UUID DEFAULT gen_random_uuid(),
  dataset_code VARCHAR(10),
  model_key VARCHAR(32),
  sample_id INTEGER REFERENCES ath.benchmark_dataset(id),
  is_province_match BOOLEAN,
  is_district_match BOOLEAN,
  is_ward_match BOOLEAN,
  is_exact_match BOOLEAN,
  confidence_score NUMERIC(5,4),
  latency_ms INTEGER,
  ran_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Bước 2: Script tạo dữ liệu benchmark (Ngày 3-7)**

```python
# scripts/generate_benchmark_datasets.py — NEW FILE
def generate_d1_urban():
    """D1: Đô thị chuẩn — lấy từ mat.ward admin_version=2"""
    ...

def generate_d2_noisy():
    """D2: Nhiễu cao — lấy D1 rồi apply noise transformations"""
    noise_transforms = [
        remove_diacritics,    # HCM -> HCM (ok), Hà Nội -> Ha Noi
        abbreviate_random,    # Quận -> Q., Phường -> P.
        introduce_typos,      # Levenshtein distance 1-2
        shuffle_components,   # Đảo thứ tự tỉnh/quận/phường
    ]
    ...

def generate_d3_pre2025():
    """D3: Pre-2025 — dùng tên đơn vị cũ từ mat.ward admin_version=1"""
    ...

def generate_d4_rural():
    """D4: Nông thôn — thôn/xóm/ấp, thiếu số nhà"""
    ...

def generate_d5_boundary():
    """D5: Ranh giới — tọa độ GPS gần biên polygon"""
    ...
```

**Deliverables:**
- [ ] `ath.benchmark_dataset` table
- [ ] `ath.benchmark_run_result` table
- [ ] `scripts/generate_benchmark_datasets.py`
- [ ] Tích hợp D1-D5 vào `experiment_runner.py`
- [ ] `GET /api/benchmark/datasets` endpoint

---

### G9. TYPESENSE SEARCH INDEX INTEGRATION ⚡ ƯU TIÊN THẤP

**Mô tả luận văn:** Sync dữ liệu sang Typesense/Elasticsearch để Hybrid Retrieval (Lexical + Semantic)

**Hiện trạng:** Config Typesense có, `sync_typesense_to_db` ngược chiều (Typesense → DB), nhưng không có logic đẩy `mat.*` vào Typesense

#### Kế hoạch thực hiện

**Bước 1: Typesense collection schema (Ngày 1-2)**

```python
# app/services/typesense_sync.py — NEW FILE
import typesense

def create_admin_unit_collection(client: typesense.Client):
    schema = {
        "name": "admin_units",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "level", "type": "string", "facet": True},
            {"name": "name", "type": "string"},
            {"name": "name_en", "type": "string", "optional": True},
            {"name": "province_id", "type": "int32", "facet": True},
            {"name": "district_id", "type": "int32", "optional": True, "facet": True},
            {"name": "admin_version", "type": "int32", "facet": True},
            {"name": "embedding", "type": "float[]", "num_dim": 768}
        ],
        "default_sorting_field": "admin_version"
    }
    client.collections.create(schema)

def sync_mat_to_typesense(db, client):
    """Đẩy toàn bộ mat.* vào Typesense collection"""
    ...
```

**Deliverables:**
- [ ] `app/services/typesense_sync.py`
- [ ] `POST /api/admin/sync-typesense` endpoint
- [ ] Tích hợp vào n8n workflow (sau khi G1 hoàn thành)

---

### G10. ĐỊNH HƯỚNG PHÁT TRIỂN (Chương 5.3)

Các tính năng trong **Định hướng phát triển** của luận văn — **không cần thiết cho luận văn** nhưng là roadmap dài hạn:

| Hướng | Mô tả | Độ phức tạp |
|-------|-------|-------------|
| H1 | Ensemble Model (PhoBERT+mGTE+Qwen3 với Confidence routing) | Cao |
| H2 | NLP trích xuất thay đổi từ PDF Nghị quyết | Rất cao |
| H3 | Reverse Geocoding đến số nhà + GNN | Rất cao |
| H4 | Privacy-Preserving (Federated Learning) | Rất cao |
| H5 | Multimodal (ASR + OCR địa chỉ) | Rất cao |

---

## 4. MA TRẬN RỦI RO & ƯU TIÊN

### 4.1 Bảng ưu tiên theo tiến độ luận văn

| # | Tính năng | Ảnh hưởng luận văn | Effort (ngày) | Ưu tiên |
|---|-----------|-------------------|---------------|---------|
| G2 | ACS đầy đủ (4 thành phần) | Chương 2.4.5 — core concept | 6 | 🔴 P0 |
| G5 | Temporal-Aware (Dual-Epoch) | Chương 1.1.3, 2.4.3 — novelty | 6 | 🔴 P0 |
| G3 | Geospatial API + 3 chiến lược | Chương 2.5, 3.4 — thực nghiệm | 13 | 🔴 P0 |
| G1 | n8n Gov-Sync — nâng cấp SCD Type 2 + Alert | Chương 2.3, 3.2 — BR1 | **4** *(rút ngắn vì n8n crawler đã có)* | 🟠 P1 |
| G8 | Benchmark D1-D5 chuẩn | Chương 4.1 — thực nghiệm | 7 | 🟠 P1 |
| G7 | PhoBERT NER BiLSTM-CRF | Chương 2.4.2, 3.3.2 | 7 | 🟡 P2 |
| G4 | Waterfall Enrichment | Chương 2.6, 5.1 | 8 | 🟡 P2 |
| G6 | FAISS Vector Index | Chương 3.3.3 | 5 | 🟡 P2 |
| G9 | Typesense Integration | Chương 2.2.1 | 4 | 🟢 P3 |

### 4.2 Lộ trình 60 ngày để hoàn thiện luận văn

```
TUẦN 1-2 (Ngày 1-14): P0 — Core Missing Features
├── G2: ACS Calculator (6 ngày)
├── G5: Epoch Detector + Temporal Routing (6 ngày)  
└── G3a: Spatial API /subdivide (2 ngày đầu trong G3)

TUẦN 3-4 (Ngày 15-28): P0 + P1
├── G3b: 3 chiến lược hiệu chỉnh polygon (11 ngày còn lại)
└── G1: Nâng cấp n8n SCD Type 2 + Alert + sync_log persist (4 ngày)
    [Tiết kiệm ~6 ngày so với kế hoạch cũ vì n8n crawler đã có]

TUẦN 5-6 (Ngày 29-42): P1 + P2
├── G8: Benchmark D1-D5 generation (7 ngày)
└── G6: FAISS Index (5 ngày)

TUẦN 7-8 (Ngày 43-56): P2 + Thực nghiệm
├── G7: PhoBERT BiLSTM-CRF training (7 ngày)
├── G4: Waterfall Enrichment (8 ngày)
└── Chạy benchmark D1-D5 đầy đủ, thu thập kết quả

TUẦN 9 (Ngày 53-56): Viết và hoàn thiện  [rút ngắn ~4 ngày]
└── Thu thập kết quả thực nghiệm, hoàn thiện Chương 4
```

### 4.3 Điều kiện tiên quyết

| Điều kiện | Trạng thái | Ghi chú |
|-----------|------------|---------|
| PostgreSQL + PostGIS | ✅ | Cần xác nhận PostGIS extension đã cài |
| `mat.area_polygon` có dữ liệu polygon | ❓ | Cần import GeoJSON từ OSM/GSO |
| GPU cho PhoBERT training | ❓ | Có thể dùng Google Colab |
| API Keys (Google Maps, VietMap) | ❓ | Cần đăng ký |
| n8n self-hosted + Browserless | ✅ | Crawler đang chạy, cron 01:00 AM (`docs/n8n/Automated Geospatial Data Extraction and Synchronization System.json`) |
| Label Studio | ✅ | Đã tích hợp endpoint |
| 100k+ mẫu địa chỉ gán nhãn | ⚠️ | Có synthetic, cần thêm gán nhãn thủ công |

---

*Tài liệu này được tạo tự động bằng AI Agent dựa trên dàn ý luận văn và phân tích codebase thực tế.*  
*Cập nhật lần cuối: 04/05/2026*
