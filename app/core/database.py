from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Numeric, BigInteger, text as sql_text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from app.core.config import Config

# Engine and Session setup
engine = create_engine(Config.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    is_active = Column(Boolean)
    type_name_en = Column(String(128))
    
    # GSO Extended Info
    admin_version = Column(Integer, default=1)
    population = Column(BigInteger)
    area_km2 = Column(Numeric(10, 2))
    decision_number = Column(String(200))
    decision_date = Column(DateTime)
    notes = Column(Text)

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
