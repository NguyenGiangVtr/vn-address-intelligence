from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Numeric, BigInteger, text as sql_text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from .config import Config

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
    __table_args__ = {'schema': 'mat'}
    
    province_id = Column(Integer, primary_key=True)
    area_id = Column(Integer)
    bonus_area_id = Column(Integer)
    country_id = Column(Integer, default=0, nullable=False)
    province_no = Column(Integer, nullable=False)
    province_name = Column(String(150), default='', nullable=False)
    type_name = Column(String(64), nullable=False)
    is_default = Column(Boolean, default=True, nullable=False)
    created_user = Column(Integer, default=0, nullable=False)
    created_date = Column(DateTime, default=func.now(), nullable=False)
    updated_user = Column(Integer, default=0, nullable=False)
    updated_date = Column(DateTime, default=func.now(), nullable=False, onupdate=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)
    province_name_en = Column(String(200))
    province_code = Column(String(5))
    served_radius = Column(Float)
    north_pole_lat = Column(Float)
    north_pole_lng = Column(Float)
    east_pole_lat = Column(Float)
    east_pole_lng = Column(Float)
    south_pole_lat = Column(Float)
    south_pole_lng = Column(Float)
    west_pole_lat = Column(Float)
    west_pole_lng = Column(Float)

class District(Base):
    __tablename__ = 'district'
    __table_args__ = {'schema': 'mat'}
    
    district_id = Column(Integer, primary_key=True)
    province_id = Column(Integer, default=0)
    district_no = Column(String(5))
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

class Ward(Base):
    __tablename__ = 'ward'
    __table_args__ = {'schema': 'mat'}
    
    ward_id = Column(Integer, primary_key=True)
    district_id = Column(Integer, default=0)
    ward_no = Column(String(5))
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

# --- DOMAIN 2: OSM Gazetteer (osm) ---

class OSMStreet(Base):
    __tablename__ = 'streets'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    province_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

class OSMBuilding(Base):
    __tablename__ = 'buildings'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    type = Column(String(100))
    created_at = Column(DateTime, default=func.now())

class OSMPoi(Base):
    __tablename__ = 'pois'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    type = Column(String(100))
    created_at = Column(DateTime, default=func.now())

class OSMRawEntity(Base):
    """Bảng lưu trữ dữ liệu 1-1 với OpenStreetMap."""
    __tablename__ = 'raw_entities'
    __table_args__ = {'schema': 'osm'}
    
    id = Column(BigInteger, primary_key=True)
    osm_type = Column(String(20)) # node, way, relation
    tags = Column(JSON)           # Lưu toàn bộ key-value tags của OSM
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

# --- DOMAIN 4: Processing Queue (prq) ---

class RawAddress(Base):
    __tablename__ = 'raw_addresses'
    __table_args__ = {'schema': 'prq'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    address_raw = Column(Text, nullable=False)
    status = Column(String(20), default='pending') # pending, ai_processed, human_reviewed, completed
    street_address = Column(Text)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=func.now())

def create_all_tables():
    init_db_schemas()
    Base.metadata.create_all(bind=engine)
