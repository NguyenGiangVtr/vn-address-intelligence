
# IMPLEMENTATION PLAN: VN Address Intelligence System
**Role:** Lead Data Engineer & Full-stack AI Developer.
**Objective:** Xây dựng kiến trúc Database và Pipeline tự động hóa cho hệ thống `vn-address-intelligence`. Hệ thống này đóng vai trò là "Trái tim dữ liệu", quản lý 4 mảng: Danh mục hành chính (Master Data), Từ vựng OpenStreetMap (OSM), Dữ liệu gán nhãn huấn luyện AI (Training Data), và Hàng đợi dữ liệu gốc cần làm sạch (Raw Queue).
Cần đóng gói gọn gàng với các phần khác trong project để có thể dễ dàng sử dụng và bảo trì.

## 1. Database Architecture (PostgreSQL: `vn_address_intelligence_db`)
Hãy tạo file `.env` với các biến environment, hệ thống sử dụng cấu hình sau:
    host: your_db_host
    port: 5432
    user: vnai_admin
    password: your_db_password
    database: vn_address_intelligence_db
    
Agent cần sử dụng SQLAlchemy ORM để thiết kế các bảng sau, phân chia theo 4 Domains:

**Lưu ý:** Các bảng master data này cần tạo đúng quy định dưới đây:
**Domain 1: Administrative Master Data (Danh mục Hành chính)**
* `schema`: `mat`
* `table`: `province`: 
```sql
CREATE TABLE mat.province (
	province_id int4 NOT NULL,
	area_id int4 NULL,
	bonus_area_id int4 NULL,
	country_id int4 DEFAULT 0 NOT NULL,
	province_no int4 NOT NULL,
	province_name varchar(150) DEFAULT ''::character varying NOT NULL,
	type_name varchar(64) NOT NULL,
	is_default bool DEFAULT true NOT NULL,
	created_user int4 DEFAULT 0 NOT NULL,
	created_date timestamp DEFAULT now() NOT NULL,
	updated_user int4 DEFAULT 0 NOT NULL,
	updated_date timestamp DEFAULT now() NOT NULL,
	is_deleted bool DEFAULT false NOT NULL,
	province_name_en varchar(200) NULL,
	province_no varchar(5) NULL,
	served_radius float8 NULL,
	north_pole_lat float8 NULL,
	north_pole_lng float8 NULL,
	east_pole_lat float8 NULL,
	east_pole_lng float8 NULL,
	south_pole_lat float8 NULL,
	south_pole_lng float8 NULL,
	west_pole_lat float8 NULL,
	west_pole_lng float8 NULL,
	CONSTRAINT province1_pkey PRIMARY KEY (province_id)
);
```
* `table`: `district`:
```sql
CREATE TABLE mat.district (
    province_id int4 DEFAULT 0 NULL,
    district_id int4 NOT NULL,
	district_no varchar(5) NULL,
	district_name varchar(150) DEFAULT ''::character varying NULL,
	type_name varchar(128) NULL,
	"location" varchar(512) NULL,
	is_default bool DEFAULT true NULL,
	created_user int4 DEFAULT 0 NULL,
	created_date timestamp DEFAULT now() NULL,
	updated_user int4 DEFAULT 0 NULL,
	updated_date timestamp DEFAULT now() NULL,
	is_deleted bool DEFAULT false NULL,
	district_name_en varchar(200) NULL,
	sfdc_id varchar(100) NULL,
	is_active bool NULL,
	type_name_en varchar(128) NULL,
	CONSTRAINT district_pkey PRIMARY KEY (district_id)
);
```
* `table`: `ward`: 
```sql
CREATE TABLE mat.ward (
	district_id int4 DEFAULT 0 NULL,
    ward_id int4 NOT NULL,
	ward_no varchar(5) NULL,
	ward_name varchar(150) DEFAULT ''::character varying NULL,
	type_name varchar(128) NULL,
	"location" varchar(512) NULL,
	is_default bool DEFAULT true NULL,
	created_user int4 DEFAULT 0 NULL,
	created_date timestamp DEFAULT now() NULL,
	updated_user int4 DEFAULT 0 NULL,
	updated_date timestamp DEFAULT now() NULL,
	is_deleted bool DEFAULT false NULL,
	ward_name_en varchar(200) NULL,
	is_active bool NULL,
	type_name_en varchar(128) NULL,
	CONSTRAINT ward_pkey PRIMARY KEY (ward_id)
);
```
**Lưu ý:** Các tên bảng và tên cột dưới đây là gợi ý, hãy linh hoạt mapping Model SQLAlchemy tương ứng.

**Domain 2: OSM Gazetteer (Từ điển OSM)**
* `schema`: `osm`
* `table`: `streets`: `id`, `name`, `province_id` (optional), `created_at`
* `table`: `buildings`: `id`, `name`, `type`, `created_at`
* `table`: `pois`: `id`, `name`, `type`, `created_at`

**Domain 3: AI Training Hub (Dữ liệu Huấn luyện NER)**
* `schema`: `ath`
* `table`: `training_datasets`:
    * `id` (PK)
    * `raw_text` (Chuỗi địa chỉ)
    * `ner_tags_json` (JSON chứa array tokens và tags chuẩn BIO)
    * `is_synthetic` (Boolean: True nếu do máy tự trộn, False nếu do người duyệt)
    * `noise_level` (Enum: low, medium, high - mức độ nhiễu)
    * `created_at`

**Domain 4: Processing Queue (Dữ liệu cần làm sạch)**
* `schema`: `prq`
* `table`: `raw_addresses`:
    * `id` (PK)
    * `raw_address` (Text gốc của user)
    * `status` (Enum: pending, ai_processed, human_reviewed, completed)
    * `street_address` (Lõi địa chỉ bóc ra)
    * `confidence_score` (Float)

## 2. Directory Structure
```text
vn_address_intelligence/
├── data/
│   └── seed/                 # Chứa file CSV/JSON danh mục hành chính gốc
├── src/
│   ├── __init__.py
│   ├── config.py             # DB URL, API keys, hằng số cấu trúc
│   ├── database.py           # SQLAlchemy setup và Models cho 4 Domains
│   ├── seeders.py            # Script import Master Data vào DB
│   ├── osm_fetcher.py        # Kéo OSM đổ vào Domain 2
│   ├── synthetic_mixer.py    # Sinh data giả lập, LƯU VÀO Domain 3 (training_datasets)
│   └── exporter.py           # Export data từ Domain 3 ra JSONL cho PhoBERT
├── requirements.txt
└── main.py                   # CLI Orchestration
```

## 3. Execution Steps (Agent Action Plan)

### Step 1: Core Architecture & Database Setup (`database.py` & `seeders.py`)
* **Action:** Setup SQLAlchemy kết nối với PostgreSQL. Thiết kế toàn bộ Models (Bảng) như đã định nghĩa ở phần 1. CHÚ Ý: Agent phải viết Raw SQL để CREATE SCHEMA `mat`, `osm`, `ath`, `prq` trước khi tạo bảng.
* **Action:** Viết script `seeders.py`. Cung cấp hàm đọc file CSV/JSON từ thư mục `data/seed/` để insert danh mục hành chính (Tỉnh, Quận, Phường) vào các bảng Master Data. (Xử lý bulk_insert để tối ưu tốc độ).

### Step 2: OSM Ingestion (`osm_fetcher.py`)
* **Action:** Gọi Overpass API tải danh sách đường, tòa nhà, POI tại Việt Nam. Điểm quan trọng là phải query lấy được các nhãn `addr:housenumber`, `addr:street` mà osm đã gán.
* **Action:** Làm sạch và lưu vào các bảng `osm.streets`, `osm.buildings`, `osm.pois`. Cần query theo từng tỉnh, quận, phường để tối ưu.

### Step 3: Synthetic Address-Line Mixer (`synthetic_mixer.py`)
**Context:** Dữ liệu thực tế của hệ thống đã có sẵn ID của 3 cấp Hành chính (Tỉnh, Quận, Phường). Mục tiêu của mô hình NER bây giờ CHỈ LÀ xử lý phần `address_line` (lõi địa chỉ ở đầu) để làm sạch nhiễu và bóc tách các thực thể nhỏ (Số nhà, Đường, Tòa nhà, Địa điểm, Ngõ/Hẻm, Khu phố/Thôn/Ấp).

* **Action:** Xây dựng Engine sinh dữ liệu giả lập chuyên biệt cho phần Lõi địa chỉ.
* **Logic Sinh Dữ liệu (Synthetic Logic):**
  1. **Fetch Core Entities:** Randomly select `[Đường]`, `[Tòa nhà]`, `[POI]` từ schema `osm` trong database.
  2. **Generate Micro Entities:** Dùng Python sinh ngẫu nhiên các giá trị cho `[Số nhà]` (VD: "12/4A", "Số 8"), `[Ngõ/Hẻm]` (VD: "Ngõ 205", "Hẻm 30"), `[Khu phố/Thôn]` (VD: "Khu phố 4", "Ấp Chánh").
  3. **Data Augmentation & Noise Injection:** Thiết kế các templates sinh chuỗi Lõi địa chỉ phức tạp giống văn phong người dùng Việt:
     * *Template 1 (Nhiễu hướng dẫn):* `[Từ_Nhiễu]` + `[POI]` + `[Đường]` -> "Đối diện Cửa hàng Ông Mão đường Ninh Hiệp"
     * *Template 2 (Siêu chi tiết):* `[Tòa nhà]` + `[Số nhà]` + `[Ngõ/Hẻm]` + `[Đường]` -> "Chung cư New City Lô B2 hẻm 12/4 Mai Chí Thọ"
     * *Template 3 (Nông thôn/Ngoại ô):* `[Khu phố/Thôn]` + `[Từ_Nhiễu]` + `[Đường]` -> "Ấp 4 nằm gần ĐT743"
     * *Thêm nhiễu ngẫu nhiên (Noise Level):* Bỏ dấu phẩy, cố tình viết tắt.
  4. **CRITICAL: Auto BIO Labeling (Gán nhãn tự động chuẩn hóa):**
     * Agent phải code logic duy trì song song mảng `tokens` và `ner_tags` với 6 nhãn chuẩn: **BLD, POI, ALY, NUM, STR, NBH**.
     * Toàn bộ từ nối và từ nhiễu ("Nằm gần", "Cạnh", "Kế bên", "Đối diện", "Khu vực") -> Gán nhãn `O`.
     * Tòa nhà/Chung cư -> Gán nhãn `B-BLD`, `I-BLD`.
     * Cửa hàng/Địa điểm -> Gán nhãn `B-POI`, `I-POI`.
     * Ngõ/Hẻm/Kiệt -> Gán nhãn `B-ALY`, `I-ALY`.
     * Số nhà/Lô -> Gán nhãn `B-NUM`, `I-NUM`.
     * Tên đường -> Gán nhãn `B-STR`, `I-STR`.
     * Khu phố/Thôn/Ấp/Xóm -> Gán nhãn `B-NBH`, `I-NBH`.
* **Storage:** LƯU KẾT QUẢ vào bảng `ath.training_datasets`. Cột `raw_text` chỉ lưu đoạn address_line giả lập (không ghép Phường/Quận/Tỉnh). Set cờ `is_synthetic = True`.

### Step 4: AI Exporter (`exporter.py`)
* **Action:** Viết hàm query bảng `ath.training_datasets`.
* Lọc dữ liệu, xuất ra file `.jsonl` chuẩn Hugging Face Token Classification với ánh xạ ID nhãn chính xác.

### Step 5: Main Orchestration (`main.py`)
* **Action:** Cung cấp CLI commands (sử dụng `argparse` hoặc `click`):
  * `python main.py init-db`
  * `python main.py seed-master`
  * `python main.py fetch-osm`
  * `python main.py generate-synthetic --count 10000`
  * `python main.py export-train-data`

## 4. Agent Constraints & Quality Checks
* **Modularity:** Bắt buộc phải chia tách logic rõ ràng. Các hàm thao tác DB phải nằm riêng biệt.
* **Error Handling:** Đảm bảo `session.rollback()` khi thao tác DB lỗi.
* **Validation:** Trước khi insert vào `ath.training_datasets`, agent PHẢI assert độ dài mảng `tokens` bằng độ dài mảng `ner_tags`.
```