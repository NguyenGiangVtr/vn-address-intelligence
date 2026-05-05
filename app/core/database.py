from __future__ import annotations
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Numeric, BigInteger, text as sql_text, Index
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from app.core.config import Config

# Engine and Session setup
engine = create_engine(Config.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Old Engine setup for mapping purposes
old_engine = create_engine(Config.OLD_SQLALCHEMY_DATABASE_URL) if Config.OLD_SQLALCHEMY_DATABASE_URL else None
OldSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=old_engine) if old_engine else None

Base = declarative_base()

def init_db_schemas():
    """Tạo các schema mat, osm, ath, prq trước khi tạo bảng."""
    with engine.connect() as conn:
        for schema in Config.SCHEMAS:
            conn.execute(sql_text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()

# --- DOMAIN 1: Administrative Master Data (mat) ---

class Province(Base):
    __tablename__ = 'province'
    __table_args__ = (
        {'schema': 'mat'},
    )
    
    row_id = Column(Integer, primary_key=True, autoincrement=True)
    province_id = Column(Integer, nullable=False)
    area_id = Column(Integer)
    bonus_area_id = Column(Integer)
    country_id = Column(Integer, default=0, nullable=False)
    province_no = Column(String(20))
    province_name = Column(String(150), default='', nullable=False)
    type_name = Column(String(64), nullable=False)
    is_default = Column(Boolean, default=True, nullable=False)
    created_user = Column(Integer, default=0, nullable=False)
    created_date = Column(DateTime, default=func.now(), nullable=False)
    updated_user = Column(Integer, default=0, nullable=False)
    updated_date = Column(DateTime, default=func.now(), nullable=False, onupdate=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)
    province_name_en = Column(String(200))
    old_id = Column(Integer) # Lưu ID từ DB cũ để tra cứu
    served_radius = Column(Float)
    north_pole_lat = Column(Float)
    north_pole_lng = Column(Float)
    east_pole_lat = Column(Float)
    east_pole_lng = Column(Float)
    south_pole_lat = Column(Float)
    south_pole_lng = Column(Float)
    west_pole_lat = Column(Float)
    west_pole_lng = Column(Float)
    
    # GSO Extended Info (admin_version 2)
    admin_version = Column(Integer, default=1) 
    population = Column(BigInteger)
    area_km2 = Column(Numeric(10, 2))
    decision_number = Column(String(200))
    decision_date = Column(DateTime)
    notes = Column(Text)

    # SCD Type 2 — Lịch sử thay đổi hành chính
    valid_from = Column(DateTime, default=func.now())
    valid_to = Column(DateTime, default=datetime(9999, 12, 31))
    is_current = Column(Boolean, default=True)
    version_id = Column(Integer, default=1)
    predecessor_id = Column(Integer, ForeignKey('mat.province.row_id'), nullable=True)

class AddressCleansingQueue(Base):
    """Hàng đợi xử lý và chuẩn hóa địa chỉ (Domain 4: prq)"""
    __tablename__ = 'address_cleansing_queue'
    __table_args__ = {'schema': 'prq'}
    
    id = Column(BigInteger, primary_key=True)
    source_system = Column(String(50))
    raw_address = Column(Text, nullable=False)
    order_count = Column(BigInteger, default=1)
    
    processing_status = Column(String(30), default='PENDING', nullable=False)
    processing_method = Column(String(30))
    error_message = Column(Text)
    
    # Administrative Data
    province_id = Column(Integer)
    province_name = Column(Text)
    district_id = Column(Integer)
    district_name = Column(Text)
    ward_id = Column(Integer)
    ward_name = Column(Text)
    
    # Core Address & AI Results
    street_address = Column(Text)
    phobert_parsed_components = Column(JSON) # jsonb
    phobert_confidence_score = Column(Numeric(5, 4))
    mgte_parsed_components = Column(JSON)
    mgte_confidence_score = Column(Numeric(5, 4))
    
    selected_ai_model = Column(String(20))
    address_standardized = Column(Text)
    postal_code = Column(String(20))
    country_code = Column(String(2), default='VN')
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    
    # Embeddings
    phobert_embedding = Column(JSON)
    mgte_embedding = Column(JSON)

    # ACS — Address Confidence Score (G2) - COMMENTED OUT: Columns don't exist in DB yet
    # acs_score    = Column(Numeric(5, 4))       # Weighted composite score [0..1]
    # acs_decision = Column(String(20))           # AUTO_ACCEPT | AUTO_CONVERT | SUGGEST | REJECT
    # s_text       = Column(Numeric(5, 4))        # Text similarity component
    # s_sem        = Column(Numeric(5, 4))        # Semantic similarity component
    # v_hierarchy  = Column(Numeric(5, 4))        # Hierarchy validity component
    # v_temporal   = Column(Numeric(5, 4))        # Temporal weight component

    # Epoch — Dual-Epoch Recognition (G5) - COMMENTED OUT: Column doesn't exist in DB yet
    # address_epoch = Column(String(20))          # PRE_2025 | POST_2025 | AMBIGUOUS

    # Additional columns that exist in DB (found during debug)
    normalized_phobert = Column(Text)
    normalized_mgte = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class District(Base):
    __tablename__ = 'district'
    __table_args__ = (
        {'schema': 'mat'},
    )
    
    row_id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(Integer, nullable=False)
    province_id = Column(Integer, default=0)
    district_no = Column(String(20))
    district_name = Column(String(150), default='')
    type_name = Column(String(128))
    location = Column(String(512))
    is_default = Column(Boolean, default=True)
    created_user = Column(Integer, default=0)
    created_date = Column(DateTime, default=func.now())
    updated_user = Column(Integer, default=0)
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    district_name_en = Column(String(200))
    old_id = Column(Integer) # Lưu ID từ DB cũ để tra cứu
    sfdc_id = Column(String(100))
    is_active = Column(Boolean)
    type_name_en = Column(String(128))
    
    # GSO Extended Info
    admin_version = Column(Integer, default=1)
    population = Column(BigInteger)
    area_km2 = Column(Numeric(10, 2))
    decision_number = Column(String(200))
    decision_date = Column(DateTime)
    notes = Column(Text)

    # SCD Type 2 — Lịch sử thay đổi hành chính
    valid_from = Column(DateTime, default=func.now())
    valid_to = Column(DateTime, default=datetime(9999, 12, 31))
    is_current = Column(Boolean, default=True)
    version_id = Column(Integer, default=1)
    predecessor_id = Column(Integer, ForeignKey('mat.district.row_id'), nullable=True)

class Ward(Base):
    __tablename__ = 'ward'
    __table_args__ = (
        {'schema': 'mat'},
    )
    
    row_id = Column(Integer, primary_key=True, autoincrement=True)
    ward_id = Column(Integer, nullable=False)
    district_id = Column(Integer, default=0)
    province_no = Column(String(20))
    ward_no = Column(String(20))
    ward_name = Column(String(150), default='')
    type_name = Column(String(128))
    location = Column(String(512))
    is_default = Column(Boolean, default=True)
    created_user = Column(Integer, default=0)
    created_date = Column(DateTime, default=func.now())
    updated_user = Column(Integer, default=0)
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    ward_name_en = Column(String(200))
    old_id = Column(Integer) # Lưu ID từ DB cũ để tra cứu
    is_active = Column(Boolean)
    type_name_en = Column(String(128))
    
    # GSO Extended Info
    admin_version = Column(Integer, default=1)
    population = Column(BigInteger)
    area_km2 = Column(Numeric(10, 2))
    decision_number = Column(String(200))
    decision_date = Column(DateTime)
    notes = Column(Text)

    # SCD Type 2 — Lịch sử thay đổi hành chính
    valid_from = Column(DateTime, default=func.now())
    valid_to = Column(DateTime, default=datetime(9999, 12, 31))
    is_current = Column(Boolean, default=True)
    version_id = Column(Integer, default=1)
    predecessor_id = Column(Integer, ForeignKey('mat.ward.row_id'), nullable=True)

# --- DOMAIN 1: Administrative Master Data (mat) Bổ sung ---

class WardMapping(Base):
    """Bảng ánh xạ thay đổi đơn vị hành chính (Sáp nhập/Đổi tên)"""
    __tablename__ = 'ward_mapping'
    __table_args__ = {'schema': 'mat'}
    
    ward_mapping_id = Column(Integer, primary_key=True)
    ward_id_old = Column(Integer)
    province_id_old = Column(Integer)
    district_id_old = Column(Integer)
    ward_id_new = Column(Integer)
    province_id_new = Column(Integer)
    district_id_new = Column(Integer)
    effective_date_from = Column(DateTime)
    effective_date_to = Column(DateTime)
    created_date = Column(DateTime, default=func.now())
    created_user = Column(Integer)
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_user = Column(Integer)
    is_deleted = Column(Boolean, default=False)
    updated_note = Column(Text)
    relationship_type = Column(String(50))
    mapping_total = Column(Integer)

class UnitEdge(Base):
    """Đồ thị quan hệ hành chính: MERGES_INTO, SPLIT_FROM, RENAMES_TO, BOUNDARY_ADJUSTED"""
    __tablename__ = 'unit_edge'
    __table_args__ = {'schema': 'mat'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_unit_id = Column(Integer, nullable=False)
    from_level = Column(String(20), nullable=False)   # 'province', 'district', 'ward'
    to_unit_id = Column(Integer, nullable=False)
    to_level = Column(String(20), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # MERGES_INTO, SPLIT_FROM, RENAMES_TO, BOUNDARY_ADJUSTED
    effective_date = Column(DateTime, nullable=False)
    resolution_ref = Column(String(200))              # Số nghị quyết
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())


class SyncLog(Base):
    """Bảng ghi nhật ký đồng bộ dữ liệu hành chính (persist)"""
    __tablename__ = 'sync_log'
    __table_args__ = {'schema': 'ath'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_source = Column(String(50))   # 'NSO_API', 'N8N_WORKFLOW', 'MANUAL'
    level = Column(String(20))         # 'province', 'district', 'ward'
    unit_id = Column(Integer)
    change_type = Column(String(30))   # 'CREATE', 'UPDATE', 'MERGE', 'RENAME', 'NO_CHANGE'
    old_value = Column(JSON)
    new_value = Column(JSON)
    synced_at = Column(DateTime, default=func.now())
    records_affected = Column(Integer, default=0)
    run_id = Column(String(50))        # UUID để nhóm các log cùng một lần chạy


class OSMStreet(Base):
    __tablename__ = 'streets'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    province_id = Column(Integer)
    province_name = Column(String(150))
    created_at = Column(DateTime, default=func.now())

class OSMBuilding(Base):
    __tablename__ = 'buildings'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    type = Column(String(100))
    province_id = Column(Integer)
    province_name = Column(String(150))
    created_at = Column(DateTime, default=func.now())

class OSMPoi(Base):
    __tablename__ = 'pois'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    type = Column(String(100))
    province_id = Column(Integer)
    province_name = Column(String(150))
    created_at = Column(DateTime, default=func.now())

class OSMRawEntity(Base):
    """Bảng lưu trữ dữ liệu 1-1 với OpenStreetMap."""
    __tablename__ = 'raw_entities'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    osm_type = Column(String(20)) # node, way, relation
    tags = Column(JSON)           # Lưu toàn bộ key-value tags của OSM
    province_id = Column(Integer)
    province_name = Column(String(150))
    created_at = Column(DateTime, default=func.now())

# --- DOMAIN 3: AI Training Hub (ath) ---

class TrainingDataset(Base):
    __tablename__ = 'training_datasets'
    __table_args__ = {'schema': 'ath'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_text = Column(Text, nullable=False)
    ner_tags_json = Column(JSON, nullable=False) # Chứa array tokens và tags chuẩn BIO
    is_synthetic = Column(Boolean, default=True)
    noise_level = Column(String(20)) # low, medium, high
    created_at = Column(DateTime, default=func.now())

class TrainingHistory(Base):
    __tablename__ = 'training_history'
    __table_args__ = {'schema': 'ath'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20))
    accuracy = Column(Float)
    f1_score = Column(Float)
    loss = Column(Float)
    samples_count = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    notes = Column(Text)


class BenchmarkModelBaseline(Base):
    __tablename__ = 'benchmark_model_baselines'
    __table_args__ = {'schema': 'ath'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_key = Column(String(32), nullable=False, unique=True)
    model_name = Column(String(120), nullable=False)
    f1 = Column(Float, nullable=False, default=0.0)
    throughput = Column(Float, nullable=False, default=0.0)
    cost_per_million = Column(Float, nullable=False, default=0.0)
    google_match = Column(Float, nullable=False, default=0.0)
    sample_size = Column(Integer, nullable=False, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AuthUser(Base):
    __tablename__ = 'auth_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(150), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(200))
    role = Column(String(50), default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class EmailVerification(Base):
    __tablename__ = 'email_verifications'
    __table_args__ = {'schema': 'ath'} # Store in AI/Auth schema

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(150), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

# --- DOMAIN 4: Processing Queue (prq) ---

class RawAddress(Base):
    __tablename__ = 'raw_addresses'
    __table_args__ = {'schema': 'prq'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_address = Column(Text, nullable=False)
    status = Column(String(20), default='pending') # pending, ai_processed, human_reviewed, completed
    street_address = Column(Text)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=func.now())

class AreaPolygon(Base):
    """Bảng lưu trữ polygon ranh giới đơn vị hành chính (PostGIS geometry)."""
    __tablename__ = 'area_polygon'
    __table_args__ = (
        Index('idx_area_polygon_unit', 'unit_level', 'unit_id'),
        {'schema': 'mat'},
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    unit_level   = Column(String(20), nullable=False)    # 'province' | 'district' | 'ward'
    unit_id      = Column(Integer, nullable=False)
    unit_name    = Column(String(200))
    geojson      = Column(JSON)                          # GeoJSON geometry object
    source       = Column(String(50), default='OSM')    # 'OSM' | 'GSO' | 'MANUAL'
    admin_version = Column(Integer, default=2)
    created_at   = Column(DateTime, default=func.now())
    updated_at   = Column(DateTime, default=func.now(), onupdate=func.now())


class BenchmarkDataset(Base):
    """Dataset chuẩn D1-D5 cho benchmark thực nghiệm (G8)."""
    __tablename__ = 'benchmark_dataset'
    __table_args__ = {'schema': 'ath'}

    id              = Column(Integer, primary_key=True, autoincrement=True)
    dataset_code    = Column(String(10), nullable=False)  # D1, D2, D3, D4, D5
    raw_address     = Column(Text, nullable=False)
    expected_ward_id   = Column(Integer)
    expected_district_id = Column(Integer)
    expected_province_id = Column(Integer)
    noise_type      = Column(String(50))        # typo, no_diacritic, abbreviation, pre_2025…
    admin_version   = Column(Integer, default=2)
    notes           = Column(Text)
    created_at      = Column(DateTime, default=func.now())


class BenchmarkRunResult(Base):
    """Kết quả chạy benchmark theo từng lần thực nghiệm (G8)."""
    __tablename__ = 'benchmark_run_result'
    __table_args__ = {'schema': 'ath'}

    id              = Column(Integer, primary_key=True, autoincrement=True)
    run_id          = Column(String(50), nullable=False)      # UUID lần chạy
    dataset_code    = Column(String(10), nullable=False)
    model_key       = Column(String(32), nullable=False)
    sample_id       = Column(Integer, ForeignKey('ath.benchmark_dataset.id'))
    predicted_ward_id   = Column(Integer)
    predicted_district_id = Column(Integer)
    predicted_province_id = Column(Integer)
    acs_score       = Column(Numeric(5, 4))
    acs_decision    = Column(String(20))
    address_epoch   = Column(String(20))
    latency_ms      = Column(Float)
    is_correct      = Column(Boolean)
    created_at      = Column(DateTime, default=func.now())


class GoogleGroundTruth(Base):
    """Dữ liệu địa chỉ chuẩn hóa (Ground Truth) từ Google/Typesense."""
    __tablename__ = 'google_ground_truth'
    __table_args__ = {'schema': 'mat'}
    
    id = Column(BigInteger, primary_key=True)
    address = Column(Text)
    old_address = Column(Text)
    ward_id = Column(Integer)
    district_id = Column(Integer)
    province_id = Column(Integer)
    old_ward_id = Column(Integer)
    old_district_id = Column(Integer)
    old_province_id = Column(Integer)
    old_address_eng = Column(Text)
    address_eng = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    popular = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def create_all_tables():
    init_db_schemas()
    Base.metadata.create_all(bind=engine)
    seed_training_metadata()


def seed_training_metadata():
    """Seed dashboard training and benchmark metadata when tables are empty."""
    training_seed_rows = [
        TrainingHistory(version="v2.1", accuracy=82.5, f1_score=79.1, loss=0.412, samples_count=12000, notes="Seed snapshot"),
        TrainingHistory(version="v2.2", accuracy=84.2, f1_score=81.5, loss=0.365, samples_count=15800, notes="Seed snapshot"),
        TrainingHistory(version="v2.3", accuracy=88.7, f1_score=85.3, loss=0.298, samples_count=20100, notes="Seed snapshot"),
        TrainingHistory(version="v2.4", accuracy=92.4, f1_score=90.1, loss=0.244, samples_count=25130, notes="Seed snapshot"),
    ]
    benchmark_seed_rows = [
        BenchmarkModelBaseline(
            model_key="phobert",
            model_name="PhoBERT",
            f1=84.2,
            throughput=27.8,
            cost_per_million=42.0,
            google_match=76.1,
            sample_size=5000,
            notes="Seed snapshot",
        ),
        BenchmarkModelBaseline(
            model_key="siamese",
            model_name="Siamese (mGTE)",
            f1=81.3,
            throughput=31.6,
            cost_per_million=28.0,
            google_match=74.5,
            sample_size=5000,
            notes="Seed snapshot",
        ),
        BenchmarkModelBaseline(
            model_key="llm",
            model_name="LLM (Qwen3)",
            f1=86.8,
            throughput=9.4,
            cost_per_million=260.0,
            google_match=82.2,
            sample_size=5000,
            notes="Seed snapshot",
        ),
    ]

    session = SessionLocal()
    try:
        if session.query(TrainingHistory).count() == 0:
            session.add_all(training_seed_rows)
            session.commit()

        if session.query(BenchmarkModelBaseline).count() == 0:
            session.add_all(benchmark_seed_rows)
            session.commit()
    finally:
        session.close()

def sync_typesense_to_db(province_id: int = None, limit: int = None):
    """
    Crawl data từ Typesense và lưu vào database.
    - province_id: Lọc theo tỉnh thành (nếu có).
    - limit: Giới hạn số lượng bản ghi.
    """
    import requests
    import json
    from sqlalchemy.dialects.postgresql import insert

    print(f"Starting sync from Typesense collection: {Config.TYPESENSE_COLLECTION}")
    
    # 1. Khởi tạo Typesense connection
    # Sử dụng requests để gọi API trực tiếp để tránh phụ thuộc thư viện bên thứ 3
    base_url = f"{Config.TYPESENSE_PROTOCOL}://{Config.TYPESENSE_HOST}:{Config.TYPESENSE_PORT}/collections/{Config.TYPESENSE_COLLECTION}/documents/search"
    headers = {
        "X-TYPESENSE-API-KEY": Config.TYPESENSE_API_KEY,
        "Content-Type": "application/json"
    }

    # 2. Xây dựng query
    batch_size = 250
    offset = 0
    total_processed = 0
    
    filter_by = f"province_id:={province_id}" if province_id else ""
    
    session = SessionLocal()
    try:
        # 0. Load Mapping Table into memory for fast lookup
        print("Loading Admin Unit Mapping for ID transformation...")
        # Sắp xếp theo admin_version tăng dần để version cao hơn sẽ ghi đè trong dictionary
        mappings = session.query(AdminUnitMapping).order_by(AdminUnitMapping.admin_version.asc()).all()
        # Tạo dictionary để lookup: (level, old_id) -> new_id
        map_dict = {(m.level, m.old_id): m.new_id for m in mappings}
        
        def get_new_id(level, old_id):
            if old_id is None: return None
            return map_dict.get((level, old_id), old_id) # Fallback về chính nó nếu không tìm thấy mapping

        while True:
            # Tính toán limit cho batch hiện tại
            # Nếu không thể filter ở server, chúng ta phải lấy batch mặc định (250) để lọc locally
            current_limit = batch_size
            if limit and (total_processed + batch_size > limit) and not filter_by:
                current_limit = limit - total_processed
            
            if current_limit <= 0:
                break

            params = {
                "q": "*",
                "per_page": batch_size, # Luôn lấy full batch để tối ưu throughput khi lọc local
                "page": (offset // batch_size) + 1
            }
            
            # Thêm filter_by nếu có thể
            if filter_by:
                params["filter_by"] = filter_by

            response = requests.get(base_url, headers=headers, params=params)
            
            # Xử lý lỗi "non-indexed field" bằng cách fallback về lấy toàn bộ và lọc local
            if response.status_code == 400 and "non-indexed field" in response.text:
                if filter_by:
                    print(f"Warning: Field 'province_id' is not indexed for filtering. Falling back to local filtering...")
                    filter_by = None # Tắt filter ở server
                    offset = 0 # Reset để lấy từ đầu
                    total_processed = 0
                    continue
                else:
                    print(f"Error calling Typesense: {response.text}")
                    break
            elif response.status_code != 200:
                print(f"Error calling Typesense: {response.text}")
                break
            
            data = response.json()
            hits = data.get("hits", [])
            if not hits:
                break
            
            # 3. Chuyển đổi và chuẩn bị dữ liệu cho database
            db_records = []
            for hit in hits:
                doc = hit["document"]
                
                # Lọc local dựa trên OLD province_id (vì typesense đang lưu OLD ID)
                doc_old_province_id = doc.get("province_id")
                if province_id is not None and doc_old_province_id != province_id:
                    continue

                # Kiểm tra giới hạn số lượng nếu lọc local
                if limit and total_processed >= limit:
                    break
                
                # Trích xuất location [lat, lon]
                location = doc.get("location", [None, None])
                lat = location[0] if len(location) > 0 else None
                lon = location[1] if len(location) > 1 else None
                
                # Thực hiện Mapping từ OLD ID -> NEW ID
                record = {
                    "id": int(doc.get("id")),
                    "address": doc.get("address"),
                    "old_address": doc.get("old_address"),
                    "province_id": get_new_id(1, doc.get("province_id")),
                    "district_id": get_new_id(2, doc.get("district_id")),
                    "ward_id": get_new_id(3, doc.get("ward_id")),
                    "old_province_id": get_new_id(1, doc.get("old_province_id")),
                    "old_district_id": get_new_id(2, doc.get("old_district_id")),
                    "old_ward_id": get_new_id(3, doc.get("old_ward_id")),
                    "old_address_eng": doc.get("old_address_eng"),
                    "address_eng": doc.get("address_eng"),
                    "latitude": lat,
                    "longitude": lon,
                    "popular": doc.get("popular", 0)
                }
                db_records.append(record)
                total_processed += 1
            
            # 4. Upsert (Merge) vào database
            if db_records:
                stmt = insert(GoogleGroundTruth).values(db_records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['id'],
                    set_={
                        k: v for k, v in record.items() if k != 'id'
                    }
                )
                session.execute(stmt)
                session.commit()
            
            offset += len(hits) # Offset dựa trên số lượng hit thực tế từ server
            
            print(f"Processed {total_processed} records (Server scanned: {offset})...")
            
            if limit and total_processed >= limit:
                break
                
            if len(hits) < batch_size:
                break
                
        print(f"Sync completed. Total records synced: {total_processed}")
        
    except Exception as e:
        print(f"Error during sync: {str(e)}")
        session.rollback()
    finally:
        session.close()
