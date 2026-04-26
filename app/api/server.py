from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import time
from datetime import datetime, timedelta
from app.core.database import SessionLocal, Province, District, Ward, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset, AddressCleansingQueue

app = FastAPI(title="VN Address Intelligence API")

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

@app.get("/style.css")
def get_css():
    return FileResponse('ui/style.css')

@app.get("/app.js")
def get_js():
    return FileResponse('ui/app.js')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Returns absolute counts and metadata for all tables."""
    return {
        "master": {
            "provinces": db.query(Province).count(),
            "districts": db.query(District).count(),
            "wards": db.query(Ward).count(),
        },
        "osm": {
            "total": db.query(OSMRawEntity).count(),
            "streets": db.query(OSMStreet).count(),
            "buildings": db.query(OSMBuilding).count(),
            "pois": db.query(OSMPoi).count(),
        },
        "ai": {
            "training_samples": db.query(TrainingDataset).count(),
            "cleansing_queue": db.query(AddressCleansingQueue).count(),
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
