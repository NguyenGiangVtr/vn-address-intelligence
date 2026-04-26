from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os
import time
import jwt
from datetime import datetime, timedelta
from app.core.database import SessionLocal, Province, District, Ward, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset, AddressCleansingQueue
from app.services.auth import verify_password, create_access_token, ALGORITHM, SECRET_KEY

app = FastAPI(title="VN Address Intelligence API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/health")
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

@app.post("/api/login")
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

@app.get("/api/stats")
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

@app.get("/api/visitors")
def get_visitor_stats():
    return {
        "total": stats_tracker.total_visits,
        "unique": len(stats_tracker.unique_ips),
        "online": stats_tracker.get_online_count()
    }

@app.get("/api/admin-v2/provinces")
def list_provinces_v2(db: Session = Depends(get_db)):
    """List provinces with versioning info."""
    provinces = db.query(Province).filter(Province.admin_version == 2).all()
    return provinces

@app.get("/api/osm/summary")
def osm_summary(db: Session = Depends(get_db)):
    return {
        "raw": db.query(OSMRawEntity).count(),
        "streets": db.query(OSMStreet).count(),
        "buildings": db.query(OSMBuilding).count(),
        "pois": db.query(OSMPoi).count()
    }

@app.get("/api/training/samples")
def training_samples(db: Session = Depends(get_db)):
    """Return top 20 training records."""
    samples = db.query(TrainingDataset).limit(20).all()
    return samples

@app.get("/api/enrichment/summary")
def enrichment_summary(db: Session = Depends(get_db)):
    """Stats on enriched data."""
    enriched_provinces = db.query(Province).filter(Province.decision_number != None).count()
    enriched_wards = db.query(Ward).filter(Ward.decision_number != None).count()
    return {
        "enriched_provinces": enriched_provinces,
        "enriched_wards": enriched_wards,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
