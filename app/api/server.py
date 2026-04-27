from fastapi import FastAPI, Depends, Request, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, aliased
from sqlalchemy import String, and_, or_
import os
import time
import jwt
from datetime import datetime, timedelta
from app.core.database import SessionLocal, Province, District, Ward, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset, AddressCleansingQueue, WardMapping
from app.services.auth import verify_password, create_access_token, ALGORITHM, SECRET_KEY
from app.services.nso_sync import sync_full_nso, sync_province_nso, sync_logs
from app.services.nso_api import get_nso_provinces, get_nso_districts, get_nso_wards
from app.api import schemas
from typing import List, Optional

app = FastAPI(
    title="VN Address Intelligence API",
    root_path="/api",
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc"
)

# Use APIRouter for cleaner route management
api_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# ── Visitor Stats State ──
class VisitorStats:
    def __init__(self):
        self.total_visits = 0
        self.unique_ips = set()
        self.online_users = {} # {ip: last_active_timestamp}

    def track(self, ip: str):
        self.total_visits += 1
        self.unique_ips.add(ip)
        self.online_users[ip] = time.time()

    def get_online_count(self):
        # Users active in the last 5 minutes
        threshold = time.time() - 300
        self.online_users = {ip: t for ip, t in self.online_users.items() if t > threshold}
        return len(self.online_users)

stats_tracker = VisitorStats()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Visitor Tracking Middleware ──
@app.middleware("http")
async def track_visitors(request: Request, call_next):
    # Get client IP (handle proxy headers if on VPS)
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0] if forwarded else request.client.host
    
    # Track only page loads and API calls, ignore static assets if needed
    if not request.url.path.startswith(("/ui", "/favicon.ico")):
        stats_tracker.track(ip)
        
    response = await call_next(request)
    return response

# Serve UI static files
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
def read_root():
    return FileResponse('ui/index.html')

@app.get("/login.html")
def read_login():
    return FileResponse('ui/login.html')

@app.get("/style.css")
def get_css():
    return FileResponse('ui/style.css')

@app.get("/app.js")
def get_js():
    return FileResponse('ui/app.js')

@app.get("/favicon.ico")
def get_favicon():
    return FileResponse('ui/login.html') # Just return something to avoid 404 for now

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@api_router.get("/health")
def health_check():
    return {"status": "ok", "time": time.time()}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except Exception:
        raise credentials_exception

@api_router.get("/provinces")
def get_provinces(version: int = 1, db: Session = Depends(get_db)):
    return db.query(Province).filter(Province.admin_version == version).order_by(Province.province_name).all()

@api_router.get("/districts/{province_id}")
def get_districts(province_id: int, version: int = 1, db: Session = Depends(get_db)):
    return db.query(District).filter(District.province_id == province_id, District.admin_version == version).order_by(District.district_name).all()

@api_router.get("/wards/{district_id}")
def get_wards(district_id: int, version: int = 1, db: Session = Depends(get_db)):
    return db.query(Ward).filter(Ward.district_id == district_id, Ward.admin_version == version).order_by(Ward.ward_name).all()

@api_router.get("/unit-details/{level}/{unit_id}")
def get_unit_details(level: str, unit_id: int, db: Session = Depends(get_db)):
    if level == "province":
        return db.query(Province).filter(Province.province_id == unit_id).first()
    if level == "district":
        return db.query(District).filter(District.district_id == unit_id).first()
    if level == "ward":
        return db.query(Ward).filter(Ward.ward_id == unit_id).first()
    return {"error": "Invalid level"}

from sqlalchemy import func

@api_router.get("/lookup/mapping")
def lookup_mapping(
    query: str = None, 
    province_id: int = None,
    district_id: int = None,
    ward_id: int = None,
    version: int = None,
    db: Session = Depends(get_db)
):
    """
    Tra cứu biến động ĐVHC bằng 1 single query (Join) chuẩn theo SQL mapping.
    """
    ProvV1 = aliased(Province)
    ProvV2 = aliased(Province)
    WardV1 = aliased(Ward)
    WardV2 = aliased(Ward)
    DistV1 = aliased(District)
    DistV2 = aliased(District)

    base_query = db.query(
        WardMapping.ward_mapping_id.label("id"),
        WardMapping.ward_id_old,
        WardMapping.ward_id_new,
        WardMapping.province_id_old,
        WardMapping.province_id_new,
        WardMapping.updated_note,
        WardMapping.effective_date_from,
        WardMapping.effective_date_to,
        WardMapping.relationship_type,
        WardMapping.mapping_total,
        
        WardV1.ward_name.label("ward_name_old"),
        WardV2.ward_name.label("ward_name_new"),
        ProvV1.province_name.label("province_name_old"),
        ProvV2.province_name.label("province_name_new"),
        WardV1.district_id.label("district_id_old"),
        DistV1.district_name.label("district_name_old"),
        WardV2.district_id.label("district_id_new"),
        DistV2.district_name.label("district_name_new")
    ).outerjoin(
        WardV1, and_(WardV1.ward_id == WardMapping.ward_id_old, WardV1.is_deleted == False, WardV1.admin_version == 1) 
    ).outerjoin(
        WardV2, and_(WardV2.ward_id == WardMapping.ward_id_new, WardV2.is_deleted == False, WardV2.admin_version == 2)
    ).outerjoin(
        DistV1, and_(DistV1.district_id == func.coalesce(WardV1.district_id, WardMapping.district_id_old), DistV1.is_deleted == False, DistV1.admin_version == 1)
    ).outerjoin(
        DistV2, and_(DistV2.district_id == WardV2.district_id, DistV2.is_deleted == False, DistV2.admin_version == 2)
    ).outerjoin(
        ProvV1, and_(ProvV1.province_id == func.coalesce(DistV1.province_id, WardMapping.province_id_old), ProvV1.is_deleted == False, ProvV1.admin_version == 1)
    ).outerjoin(
        ProvV2, and_(ProvV2.province_id == func.coalesce(DistV2.province_id, WardMapping.province_id_new), ProvV2.is_deleted == False, ProvV2.admin_version == 2)
    )

    filters = []

    if province_id:
        if version == 1:
            filters.append(or_(
                WardMapping.province_id_old == province_id, 
                DistV1.province_id == province_id,
                ProvV1.province_id == province_id
            ))
        elif version == 2:
            filters.append(or_(
                WardMapping.province_id_new == province_id, 
                DistV2.province_id == province_id,
                ProvV2.province_id == province_id
            ))
        else:
            filters.append(or_(
                WardMapping.province_id_old == province_id,
                WardMapping.province_id_new == province_id,
                DistV1.province_id == province_id,
                DistV2.province_id == province_id,
                ProvV1.province_id == province_id,
                ProvV2.province_id == province_id
            ))
    
    if district_id:
        if version == 1:
            filters.append(or_(
                WardMapping.district_id_old == district_id, 
                WardV1.district_id == district_id,
                DistV1.district_id == district_id
            ))
        elif version == 2:
            filters.append(or_(
                WardMapping.district_id_new == district_id, 
                WardV2.district_id == district_id,
                DistV2.district_id == district_id
            ))
        else:
            filters.append(or_(
                WardMapping.district_id_old == district_id,
                WardMapping.district_id_new == district_id,
                WardV1.district_id == district_id,
                WardV2.district_id == district_id,
                DistV1.district_id == district_id,
                DistV2.district_id == district_id
            ))
            
    if ward_id:
        if version == 1:
            filters.append(WardMapping.ward_id_old == ward_id)
        elif version == 2:
            filters.append(WardMapping.ward_id_new == ward_id)
        else:
            filters.append((WardMapping.ward_id_old == ward_id) | (WardMapping.ward_id_new == ward_id))
    
    if query:
        text_filter = (
            WardMapping.updated_note.ilike(f"%{query}%") |
            WardMapping.ward_id_old.cast(String).ilike(f"%{query}%") |
            WardMapping.ward_id_new.cast(String).ilike(f"%{query}%")
        )
        filters.append(text_filter)

    # Nếu có filter thì áp dụng, nếu không có thể trả về tất cả hoặc mảng rỗng tùy logic
    if filters:
        base_query = base_query.filter(and_(*filters))
    else:
        return []

    # Lấy dữ liệu và giới hạn kết quả
    # 4. Sắp xếp kết quả theo Tên (Province -> District -> Ward)
    results = base_query.order_by(
        ProvV1.province_name.asc(),
        DistV1.district_name.asc(),
        WardV1.ward_name.asc()
    ).limit(100).all()

    # 4. Format lại output và xử lý các case đặc biệt (-1)
    enriched_results = []
    for r in results:
        # Rút trích dict từ result tuple
        res = r._asdict()
        
        # Xử lý trường hợp đặc biệt (Sáp nhập cấp tỉnh: ward_id = -1)
        if res["ward_id_old"] == -1 and res["ward_id_new"] == -1:
            res["ward_name_old"] = res["ward_name_old"] or "(Tất cả Xã)"
            res["district_name_old"] = res["district_name_old"] or "(Tất cả Huyện)"
            res["ward_name_new"] = res["ward_name_new"] or "(Tất cả Xã)"
            res["district_name_new"] = res["district_name_new"] or "(Tất cả Huyện)"
        elif res["ward_id_old"] == -1:
            res["ward_name_old"] = "(Toàn bộ Huyện)"
            
        enriched_results.append(res)

    return enriched_results

@api_router.post("/sync/nso")
def trigger_nso_sync(db: Session = Depends(get_db)):
    """Kích hoạt đồng bộ dữ liệu từ NSO (danhmuchanhchinh.nso.gov.vn)"""
    # This should ideally be a background task
    result = sync_full_nso(db)
    return result

@api_router.post("/sync/nso/province")
async def trigger_nso_province_sync(data: dict, db: Session = Depends(get_db)):
    """Đồng bộ một tỉnh cụ thể từ NSO (Batch sync)"""
    p_code = data.get("code")
    p_name = data.get("name")
    if not p_code or not p_name:
        raise HTTPException(status_code=400, detail="Thiếu mã hoặc tên tỉnh")
    
    # Run sync (Ideally background, but for batch we try sync for now)
    return sync_province_nso(db, p_code, p_name)

@api_router.get("/sync/nso/logs")
def get_sync_logs():
    """Lấy danh sách log đồng bộ realtime"""
    return sync_logs

@api_router.delete("/sync/nso/logs")
def clear_sync_logs():
    """Xóa danh sách log"""
    sync_logs.clear()
    return {"status": "cleared"}

# ── NSO LIVE DATA ENDPOINTS ──

@api_router.get("/nso/provinces", tags=["NSO External"])
def fetch_nso_provinces(date: str = None):
    """Lấy danh sách Tỉnh từ NSO (DMDVHC.asmx)"""
    try:
        return get_nso_provinces(date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@api_router.get("/nso/districts", tags=["NSO External"])
def fetch_nso_districts(province_no: str = "", province_name: str = "", date: str = None):
    """Lấy danh sách Quận/Huyện từ NSO (DMDVHC.asmx)"""
    try:
        return get_nso_districts(province_no, province_name, date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@api_router.get("/nso/wards", tags=["NSO External"])
def fetch_nso_wards(province_no: str = "", province_name: str = "", district_no: str = "", district_name: str = "", date: str = None):
    """Lấy danh sách Phường/Xã từ NSO (DMDVHC.asmx)"""
    try:
        return get_nso_wards(province_no, province_name, district_no, district_name, date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@api_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Simple hardcoded admin for now (should be in DB later)
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "vnai@2026")
    
    print(f"Login attempt for user: {form_data.username}")
    
    if form_data.username != ADMIN_USER or form_data.password != ADMIN_PASS:
        print(f"Login failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"Login successful for user: {form_data.username}")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Returns absolute counts and metadata for all tables. Robust version."""
    def safe_count(query):
        try:
            return query.count()
        except Exception as e:
            print(f"Stats Error: {e}")
            return 0

    return {
        "master": {
            "provinces": safe_count(db.query(Province)),
            "districts": safe_count(db.query(District)),
            "wards": safe_count(db.query(Ward)),
            "mappings": safe_count(db.query(WardMapping))
        },
        "osm": {
            "total": safe_count(db.query(OSMRawEntity)),
            "streets": safe_count(db.query(OSMStreet)),
            "buildings": safe_count(db.query(OSMBuilding)),
            "pois": safe_count(db.query(OSMPoi)),
        },
        "ai": {
            "training_samples": safe_count(db.query(TrainingDataset)),
            "cleansing_queue": safe_count(db.query(AddressCleansingQueue)),
        },
        "visitors": {
            "total": stats_tracker.total_visits,
            "unique": len(stats_tracker.unique_ips),
            "online": stats_tracker.get_online_count()
        }
    }

@api_router.get("/visitors")
def get_visitor_stats():
    return {
        "total": stats_tracker.total_visits,
        "unique": len(stats_tracker.unique_ips),
        "online": stats_tracker.get_online_count()
    }

@api_router.get("/admin-v2/provinces")
def list_provinces_v2(db: Session = Depends(get_db)):
    """List provinces with versioning info."""
    provinces = db.query(Province).filter(Province.admin_version == 2).all()
    return provinces

@api_router.get("/osm/summary")
def osm_summary(db: Session = Depends(get_db)):
    return {
        "raw": db.query(OSMRawEntity).count(),
        "streets": db.query(OSMStreet).count(),
        "buildings": db.query(OSMBuilding).count(),
        "pois": db.query(OSMPoi).count()
    }

@api_router.get("/training/samples")
def training_samples(db: Session = Depends(get_db)):
    """Return top 20 training records."""
    samples = db.query(TrainingDataset).limit(20).all()
    return samples

@api_router.get("/enrichment/summary")
def enrichment_summary(db: Session = Depends(get_db)):
    """Stats on enriched data."""
    enriched_provinces = db.query(Province).filter(Province.decision_number != None).count()
    enriched_wards = db.query(Ward).filter(Ward.decision_number != None).count()
    return {
        "enriched_provinces": enriched_provinces,
        "enriched_wards": enriched_wards,
    }

# ── PROVINCE CRUD ──
@api_router.get("/provinces", response_model=List[schemas.ProvinceResponse], tags=["Administrative"])
def get_provinces(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Province).offset(skip).limit(limit).all()

@api_router.post("/provinces", response_model=schemas.ProvinceResponse, tags=["Administrative"])
def create_province(province: schemas.ProvinceCreate, db: Session = Depends(get_db)):
    db_province = Province(**province.dict())
    db.add(db_province)
    db.commit()
    db.refresh(db_province)
    return db_province

@api_router.get("/provinces/{province_id}", response_model=schemas.ProvinceResponse, tags=["Administrative"])
def get_province(province_id: int, db: Session = Depends(get_db)):
    db_province = db.query(Province).filter(Province.province_id == province_id).first()
    if not db_province:
        raise HTTPException(status_code=404, detail="Province not found")
    return db_province

@api_router.patch("/provinces/{province_id}", response_model=schemas.ProvinceResponse, tags=["Administrative"])
def update_province(province_id: int, province: schemas.ProvinceUpdate, db: Session = Depends(get_db)):
    db_province = db.query(Province).filter(Province.province_id == province_id).first()
    if not db_province:
        raise HTTPException(status_code=404, detail="Province not found")
    
    update_data = province.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_province, key, value)
    
    db.commit()
    db.refresh(db_province)
    return db_province

@api_router.delete("/provinces/{province_id}", tags=["Administrative"])
def delete_province(province_id: int, db: Session = Depends(get_db)):
    db_province = db.query(Province).filter(Province.province_id == province_id).first()
    if not db_province:
        raise HTTPException(status_code=404, detail="Province not found")
    db.delete(db_province)
    db.commit()
    return {"status": "success", "message": "Province deleted"}

# ── DISTRICT CRUD ──
@api_router.get("/districts", response_model=List[schemas.DistrictResponse], tags=["Administrative"])
def get_districts(province_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(District)
    if province_id:
        query = query.filter(District.province_id == province_id)
    return query.offset(skip).limit(limit).all()

@api_router.post("/districts", response_model=schemas.DistrictResponse, tags=["Administrative"])
def create_district(district: schemas.DistrictCreate, db: Session = Depends(get_db)):
    db_district = District(**district.dict())
    db.add(db_district)
    db.commit()
    db.refresh(db_district)
    return db_district

@api_router.get("/districts/{district_id}", response_model=schemas.DistrictResponse, tags=["Administrative"])
def get_district(district_id: int, db: Session = Depends(get_db)):
    db_district = db.query(District).filter(District.district_id == district_id).first()
    if not db_district:
        raise HTTPException(status_code=404, detail="District not found")
    return db_district

@api_router.patch("/districts/{district_id}", response_model=schemas.DistrictResponse, tags=["Administrative"])
def update_district(district_id: int, district: schemas.DistrictUpdate, db: Session = Depends(get_db)):
    db_district = db.query(District).filter(District.district_id == district_id).first()
    if not db_district:
        raise HTTPException(status_code=404, detail="District not found")
    
    update_data = district.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_district, key, value)
    
    db.commit()
    db.refresh(db_district)
    return db_district

@api_router.delete("/districts/{district_id}", tags=["Administrative"])
def delete_district(district_id: int, db: Session = Depends(get_db)):
    db_district = db.query(District).filter(District.district_id == district_id).first()
    if not db_district:
        raise HTTPException(status_code=404, detail="District not found")
    db.delete(db_district)
    db.commit()
    return {"status": "success", "message": "District deleted"}

# ── WARD CRUD ──
@api_router.get("/wards", response_model=List[schemas.WardResponse], tags=["Administrative"])
def get_wards(district_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Ward)
    if district_id:
        query = query.filter(Ward.district_id == district_id)
    return query.offset(skip).limit(limit).all()

@api_router.post("/wards", response_model=schemas.WardResponse, tags=["Administrative"])
def create_ward(ward: schemas.WardCreate, db: Session = Depends(get_db)):
    db_ward = Ward(**ward.dict())
    db.add(db_ward)
    db.commit()
    db.refresh(db_ward)
    return db_ward

@api_router.get("/wards/{ward_id}", response_model=schemas.WardResponse, tags=["Administrative"])
def get_ward(ward_id: int, db: Session = Depends(get_db)):
    db_ward = db.query(Ward).filter(Ward.ward_id == ward_id).first()
    if not db_ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    return db_ward

@api_router.patch("/wards/{ward_id}", response_model=schemas.WardResponse, tags=["Administrative"])
def update_ward(ward_id: int, ward: schemas.WardUpdate, db: Session = Depends(get_db)):
    db_ward = db.query(Ward).filter(Ward.ward_id == ward_id).first()
    if not db_ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    
    update_data = ward.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ward, key, value)
    
    db.commit()
    db.refresh(db_ward)
    return db_ward

@api_router.delete("/wards/{ward_id}", tags=["Administrative"])
def delete_ward(ward_id: int, db: Session = Depends(get_db)):
    db_ward = db.query(Ward).filter(Ward.ward_id == ward_id).first()
    if not db_ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    db.delete(db_ward)
    db.commit()
    return {"status": "success", "message": "Ward deleted"}

# Register API router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    # Changed port to 8081 to match VPS setup (avoiding 8080 which might be used by Docker)
    uvicorn.run(app, host="0.0.0.0", port=8081)
