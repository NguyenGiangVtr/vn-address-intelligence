from fastapi import FastAPI, Depends, Request, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import String
import os
import time
import jwt
from datetime import datetime, timedelta
from app.core.database import SessionLocal, Province, District, Ward, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset, AddressCleansingQueue, WardMapping
from app.services.auth import verify_password, create_access_token, ALGORITHM, SECRET_KEY
from app.services.nso_sync import sync_full_nso

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

@api_router.get("/lookup/mapping")
def lookup_mapping(
    query: str = None, 
    province_id: int = None,
    district_id: int = None,
    ward_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Tra cứu biến động ĐVHC. Ưu tiên tra cứu chính xác theo ID nếu có.
    """
    filters = []
    
    # 1. Nếu có ID cụ thể, ưu tiên tra cứu chính xác theo ID
    if ward_id:
        filters.append((WardMapping.ward_id_old == ward_id) | (WardMapping.ward_id_new == ward_id))
    elif district_id:
        filters.append(WardMapping.district_id_old == district_id)
        # Nếu chọn tới cấp Huyện mà không chọn Xã: lấy các bản ghi thay đổi của Huyện đó
        filters.append(WardMapping.ward_id_old == -1)
    elif province_id:
        # Nếu chỉ chọn Tỉnh: lấy các bản ghi thay đổi cấp Tỉnh (ward_id_old = -1 và ward_id_new = -1)
        filters.append((WardMapping.province_id_old == province_id) | (WardMapping.province_id_new == province_id))
        filters.append(WardMapping.ward_id_old == -1)
        filters.append(WardMapping.ward_id_new == -1)
    
    # 2. Nếu có query text (từ ô search tự do), tìm trong note và cast ID
    if query:
        text_filter = (
            (WardMapping.updated_note.ilike(f"%{query}%")) |
            (WardMapping.ward_id_old.cast(String).ilike(f"%{query}%")) |
            (WardMapping.ward_id_new.cast(String).ilike(f"%{query}%"))
        )
        filters.append(text_filter)

    if not filters:
        return []

    from sqlalchemy import and_
    mappings = db.query(WardMapping).filter(and_(*filters)).order_by(WardMapping.effective_date_from.desc()).limit(100).all()
    
    # 3. Enrich dữ liệu với Tên
    enriched_results = []
    for m in mappings:
        res = {
            "id": m.ward_mapping_id,
            "ward_id_old": m.ward_id_old,
            "ward_id_new": m.ward_id_new,
            "district_id_old": m.district_id_old,
            "province_id_old": m.province_id_old,
            "province_id_new": m.province_id_new,
            "updated_note": m.updated_note,
            "effective_date_from": m.effective_date_from,
            "effective_date_to": m.effective_date_to,
            "relationship_type": m.relationship_type,
            "mapping_total": m.mapping_total,
            
            "ward_name_old": "",
            "district_name_old": "",
            "province_name_old": "",
            "ward_name_new": "",
            "province_name_new": ""
        }
        
        # ── XỬ LÝ TÊN CŨ (V1) ──
        if m.ward_id_old and m.ward_id_old != -1:
            w_old = db.query(Ward).filter(Ward.ward_id == m.ward_id_old, Ward.admin_version == 1).first()
            if w_old:
                res["ward_name_old"] = w_old.ward_name
                # Nếu record mapping thiếu district_id_old, lấy từ bản ghi Ward
                if not m.district_id_old: m.district_id_old = w_old.district_id
        
        if m.district_id_old and m.district_id_old != -1:
            d_old = db.query(District).filter(District.district_id == m.district_id_old, District.admin_version == 1).first()
            if d_old:
                res["district_name_old"] = d_old.district_name
                if not m.province_id_old: m.province_id_old = d_old.province_id
        
        if m.province_id_old and m.province_id_old != -1:
            p_old = db.query(Province).filter(Province.province_id == m.province_id_old, Province.admin_version == 1).first()
            if p_old: res["province_name_old"] = p_old.province_name

        # ── XỬ LÝ TÊN MỚI (V2) ──
        if m.ward_id_new and m.ward_id_new != -1:
            w_new = db.query(Ward).filter(Ward.ward_id == m.ward_id_new, Ward.admin_version == 2).first()
            if w_new:
                res["ward_name_new"] = w_new.ward_name
                if not m.province_id_new: m.province_id_new = w_new.province_id
        
        if m.province_id_new and m.province_id_new != -1:
            p_new = db.query(Province).filter(Province.province_id == m.province_id_new, Province.admin_version == 2).first()
            if p_new: res["province_name_new"] = p_new.province_name

        # ── XỬ LÝ TRƯỜNG HỢP ĐẶC BIỆT: SÁP NHẬP TỈNH (WARD_ID = -1) ──
        if m.ward_id_old == -1 and m.ward_id_new == -1:
            if not res["ward_name_old"]: res["ward_name_old"] = "(Tất cả Xã)"
            if not res["district_name_old"]: res["district_name_old"] = "(Tất cả Huyện)"
        elif m.ward_id_old == -1:
            res["ward_name_old"] = "(Toàn bộ Huyện)"

        enriched_results.append(res)
        
    return enriched_results

@api_router.post("/sync/nso")
def trigger_nso_sync(db: Session = Depends(get_db)):
    """Kích hoạt đồng bộ dữ liệu từ NSO (danhmuchanhchinh.nso.gov.vn)"""
    # This should ideally be a background task
    result = sync_full_nso(db)
    return result

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

# Register API router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    # Changed port to 8081 to match VPS setup (avoiding 8080 which might be used by Docker)
    uvicorn.run(app, host="0.0.0.0", port=8081)
