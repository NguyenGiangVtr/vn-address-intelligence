from fastapi import FastAPI, Depends, Request, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, aliased
from sqlalchemy import String, and_, or_, text
import os
import logging
import time
import re
import jwt
import sys
import subprocess
import threading
import traceback
import httpx
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from app.core.database import SessionLocal, Province, District, Ward, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset, TrainingHistory, BenchmarkModelBaseline, AddressCleansingQueue, WardMapping, seed_training_metadata
from app.services.auth import verify_password, create_access_token, ALGORITHM, SECRET_KEY
from app.services.nso_sync import sync_full_nso, sync_province_nso, sync_logs
from app.services.nso_api import get_nso_provinces, get_nso_districts, get_nso_wards
from app.api import schemas
from typing import List, Optional

# ── Logging Setup ──
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s — %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("VNAI_Server")

app = FastAPI(
    title="VN Address Intelligence API",
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

# ── Benchmark Job State ──
benchmark_job_lock = threading.Lock()
benchmark_job_state = {
    "jobId": None,
    "status": "idle",  # idle | running | success | failed
    "startedAt": None,
    "finishedAt": None,
    "configPath": None,
    "skipLLM": False,
    "exitCode": None,
    "error": None,
    "outputTail": None,
}

osm_job_lock = threading.Lock()
osm_job_state = {
    "jobId": None,
    "status": "idle",  # idle | running | success | failed
    "startedAt": None,
    "finishedAt": None,
    "limitProvinces": 63,
    "targetTotal": 5000000,
    "normalizedTargetTotal": 5000000,
    "exitCode": None,
    "error": None,
    "outputTail": None,
}

parser_runtime_lock = threading.Lock()
parser_runtime_bundle = None


def _normalize_int_value(value: object, default: int) -> int:
    """Normalize numeric payload values that may include formatting separators.

    Args:
        value: Incoming payload value.
        default: Fallback used when the value is missing or invalid.

    Returns:
        A non-negative integer parsed from the provided value.
    """
    if value is None:
        return default

    if isinstance(value, int):
        return max(0, value)

    cleaned_value = re.sub(r"[^0-9]", "", str(value))
    if not cleaned_value:
        return default

    try:
        return max(0, int(cleaned_value))
    except ValueError:
        return default


def _update_benchmark_job_state(**kwargs):
    with benchmark_job_lock:
        benchmark_job_state.update(kwargs)


def _run_benchmark_job(job_id: str, config_path: str, skip_llm: bool):
    project_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "app.ai.experiment_runner",
        "--config",
        config_path,
    ]
    if skip_llm:
        cmd.append("--no-llm")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
        output_tail = (proc.stdout or "")
        if proc.stderr:
            output_tail += "\n" + proc.stderr
        output_tail = output_tail[-6000:] if output_tail else ""

        if proc.returncode == 0:
            _update_benchmark_job_state(
                status="success",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=proc.returncode,
                error=None,
                outputTail=output_tail,
            )
        else:
            _update_benchmark_job_state(
                status="failed",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=proc.returncode,
                error=f"Benchmark process exited with code {proc.returncode}",
                outputTail=output_tail,
            )
    except Exception as exc:
        _update_benchmark_job_state(
            status="failed",
            finishedAt=datetime.utcnow().isoformat() + "Z",
            exitCode=-1,
            error=f"{exc}\n{traceback.format_exc()}",
            outputTail=None,
        )


def _update_osm_job_state(**kwargs):
    with osm_job_lock:
        osm_job_state.update(kwargs)


def _run_osm_job(job_id: str, limit_provinces: int, target_total: int):
    project_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "app.main",
        "fetch-osm",
        "--limit",
        str(limit_provinces),
        "--target",
        str(target_total),
    ]

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        output_tail = ""
        if proc.stdout is not None:
            for raw_line in proc.stdout:
                line = raw_line.rstrip("\n")
                if not line:
                    continue

                output_tail = (output_tail + "\n" + line).strip()[-6000:]
                _update_osm_job_state(outputTail=output_tail)

        return_code = proc.wait()

        if return_code == 0:
            _update_osm_job_state(
                status="success",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                error=None,
                outputTail=output_tail,
            )
        else:
            _update_osm_job_state(
                status="failed",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                error=f"OSM process exited with code {return_code}",
                outputTail=output_tail,
            )
    except Exception as exc:
        _update_osm_job_state(
            status="failed",
            finishedAt=datetime.utcnow().isoformat() + "Z",
            exitCode=-1,
            error=f"{exc}\n{traceback.format_exc()}",
            outputTail=None,
        )


def _serialize_parser_sample(sample: AddressCleansingQueue) -> dict:
    return {
        "id": sample.id,
        "raw_address": sample.raw_address,
        "street_address": sample.street_address,
        "ward_name": sample.ward_name,
        "district_name": sample.district_name,
        "province_name": sample.province_name,
        "address_standardized": sample.address_standardized,
        "selected_ai_model": sample.selected_ai_model,
        "processing_status": sample.processing_status,
        "processing_method": sample.processing_method,
        "updated_at": sample.updated_at.isoformat() + "Z" if sample.updated_at else None,
    }


def _load_parser_corpus(db: Session) -> list[str]:
    corpus: list[str] = []

    standardized_rows = (
        db.query(AddressCleansingQueue.address_standardized)
        .filter(AddressCleansingQueue.address_standardized.isnot(None))
        .distinct()
        .limit(5000)
        .all()
    )
    corpus = [row[0] for row in standardized_rows if row and row[0]]

    if corpus:
        return corpus

    hierarchy_rows = (
        db.query(Ward.ward_name, District.district_name, Province.province_name)
        .join(District, Ward.district_id == District.district_id)
        .join(Province, District.province_id == Province.province_id)
        .filter(Ward.is_deleted == False, District.is_deleted == False, Province.is_deleted == False)
        .limit(5000)
        .all()
    )
    return [f"{ward}, {district}, {province}" for ward, district, province in hierarchy_rows if ward and district and province]


def _build_parser_runtime_bundle() -> dict:
    """Load AI models for parser research. Handles errors gracefully."""
    from app.ai.models import LLMQwen3, PhoBERTSiamese, SiameseMGTE
    from app.ai.export_for_annotation import PreLabeler

    bundle = {
        "phobert": None,
        "mgte": None,
        "llm": None,
        "prelabeler": PreLabeler,
        "corpus": [],
        "errors": {}
    }

    try:
        with SessionLocal() as db:
            bundle["corpus"] = _load_parser_corpus(db)
    except Exception as e:
        logger.error(f"❌ Failed to load parser corpus: {e}")
        bundle["errors"]["corpus"] = str(e)

    # Load PhoBERT
    try:
        phobert = PhoBERTSiamese(model_name="vinai/phobert-base", device="auto")
        if bundle["corpus"]:
            phobert.encode_corpus(bundle["corpus"])
        bundle["phobert"] = phobert
    except Exception as e:
        logger.error(f"❌ Failed to load PhoBERT: {e}")
        bundle["errors"]["phobert"] = str(e)

    # Load mGTE
    try:
        mgte = SiameseMGTE(model_name="Alibaba-NLP/gte-multilingual-base", device="auto")
        if bundle["corpus"]:
            mgte.encode_corpus(bundle["corpus"])
        bundle["mgte"] = mgte
    except Exception as e:
        logger.error(f"❌ Failed to load mGTE: {e}")
        bundle["errors"]["mgte"] = str(e)

    # Load LLM (Use a more realistic model name: Qwen2.5-1.5B-Instruct is small and fast)
    try:
        llm = LLMQwen3(model_name="Qwen/Qwen2.5-1.5B-Instruct", use_quantization=False, device="auto")
        bundle["llm"] = llm
    except Exception as e:
        logger.error(f"❌ Failed to load LLM: {e}")
        bundle["errors"]["llm"] = str(e)

    return bundle


def _get_parser_runtime_bundle() -> dict:
    global parser_runtime_bundle
    with parser_runtime_lock:
        if parser_runtime_bundle is None:
            parser_runtime_bundle = _build_parser_runtime_bundle()
        return parser_runtime_bundle


def _get_random_parser_sample(db: Session) -> AddressCleansingQueue:
    return (
        db.query(AddressCleansingQueue)
        .filter(AddressCleansingQueue.raw_address.isnot(None))
        .order_by(text("random()"))
        .first()
    )


def _run_parser_research(sample: AddressCleansingQueue) -> dict:
    bundle = _get_parser_runtime_bundle()
    raw_address = sample.raw_address or ""
    ward_name = sample.ward_name
    district_name = sample.district_name
    province_name = sample.province_name

    def _build_llm_candidates() -> list[str]:
        corpus = bundle.get("corpus") or []
        mgte = bundle.get("mgte")
        if not corpus or not mgte or not getattr(mgte, "_corpus_emb", None):
            return []

        import numpy as np
        try:
            q_emb = mgte.model.encode([raw_address], normalize_embeddings=True, convert_to_numpy=True)[0]
            scores = mgte._corpus_emb @ q_emb
            top_idx = np.argsort(scores)[::-1][:5]
            return [corpus[int(i)] for i in top_idx]
        except:
            return []

    outputs = {}

    # 1. PreLabeler (Always available)
    try:
        outputs["prelabeler"] = {
            "mode": "rule_based_hybrid",
            "result": bundle["prelabeler"].predict(raw_address, ward_name, district_name, province_name),
            "entityCount": 0,
        }
        outputs["prelabeler"]["entityCount"] = len(outputs["prelabeler"]["result"])
    except Exception as e:
        outputs["prelabeler"] = {"error": str(e)}

    # 2. PhoBERT
    if bundle.get("phobert"):
        try:
            norm, score, lat = bundle["phobert"].normalize(raw_address)
            outputs["phobert"] = {
                "mode": "phoBERT_siamese",
                "normalizedAddress": norm,
                "score": round(score, 4),
                "latencyMs": round(lat, 2),
            }
        except Exception as e:
            outputs["phobert"] = {"error": str(e)}
    else:
        outputs["phobert"] = {"status": "Not loaded", "error": bundle["errors"].get("phobert")}

    # 3. mGTE
    if bundle.get("mgte"):
        try:
            norm, score, lat = bundle["mgte"].normalize(raw_address)
            outputs["mgte"] = {
                "mode": "mGTE_siamese",
                "normalizedAddress": norm,
                "score": round(score, 4),
                "latencyMs": round(lat, 2),
            }
        except Exception as e:
            outputs["mgte"] = {"error": str(e)}
    else:
        outputs["mgte"] = {"status": "Not loaded", "error": bundle["errors"].get("mgte")}

    # 4. LLM
    if bundle.get("llm"):
        try:
            candidates = _build_llm_candidates()
            norm, score, lat = bundle["llm"].normalize(raw_address, candidates)
            outputs["llm"] = {
                "mode": "qwen2.5_llm",
                "normalizedAddress": norm if isinstance(norm, str) else norm.get("full_address") if isinstance(norm, dict) else str(norm),
                "score": round(score, 4),
                "latencyMs": round(lat, 2),
            }
        except Exception as e:
            outputs["llm"] = {"error": str(e)}
    else:
        outputs["llm"] = {"status": "Not loaded", "error": bundle["errors"].get("llm")}

    return {
        "sample": _serialize_parser_sample(sample),
        "analysis_input": raw_address,
        "outputs": outputs,
        "meta": {
            "corpusSize": len(bundle.get("corpus") or []),
            "evaluatedAt": datetime.utcnow().isoformat() + "Z",
            "note": "Research comparison matrix. First run loads AI models which may cause initial delay.",
        },
    }

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
app.mount("/pages", StaticFiles(directory="ui/pages"), name="pages")

@app.get("/")
@app.get("/index.html")
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

@app.get("/controls-template.js")
def get_controls_template_js():
    return FileResponse('ui/controls-template.js')

@app.get("/{page_name}.html")
def get_any_html(page_name: str):
    # Try ui/ first
    p1 = Path(f"ui/{page_name}.html")
    if p1.exists():
        return FileResponse(p1)
    # Try ui/pages/ next
    p2 = Path(f"ui/pages/{page_name}.html")
    if p2.exists():
        return FileResponse(p2)
    raise HTTPException(status_code=404)

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
def get_provinces(version: Optional[int] = 1, db: Session = Depends(get_db)):
    """Fetch all provinces, filtered by admin version."""
    return db.query(Province).filter(Province.admin_version == version).order_by(Province.province_name).all()

@api_router.get("/districts/{province_id}")
def get_districts(province_id: int, version: Optional[int] = 1, db: Session = Depends(get_db)):
    """Fetch districts by province ID and version."""
    return db.query(District).filter(District.province_id == province_id, District.admin_version == version).order_by(District.district_name).all()

@api_router.get("/wards/{district_id}")
def get_wards(district_id: int, version: Optional[int] = 1, db: Session = Depends(get_db)):
    """Fetch wards by district ID and version."""
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

    # Nếu có filter hoặc query thì áp dụng
    if filters:
        base_query = base_query.filter(and_(*filters))
    elif not query:
        # Nếu không có gì cả, không trả về gì để tránh query quá nặng
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
    
    logger.info(f"Login attempt for user: {form_data.username}")
    
    if form_data.username != ADMIN_USER or form_data.password != ADMIN_PASS:
        logger.warning(f"Login failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"Login successful for user: {form_data.username}")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Returns absolute counts and metadata for all tables. Robust version."""
    def safe_count(query):
        try:
            return query.count()
        except Exception as e:
            logger.error(f"Stats Error: {e}")
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


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def _similarity_ratio(a: Optional[str], b: Optional[str]) -> float:
    na = _normalize_text(a)
    nb = _normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


@api_router.get("/benchmark/realtime")
def get_benchmark_realtime(db: Session = Depends(get_db)):
    """
    Trả về benchmark real-time cho 3 mô hình từ dữ liệu DB hiện tại.
    Ưu tiên đo theo dữ liệu đã chạy benchmark nếu có cột normalized_*.
    """

    target_schema = "prq"
    target_table = "address_cleansing_queue"

    # Baseline fallback để UI luôn render được nếu DB chưa đủ cột benchmark.
    models = {
        "phobert": {
            "name": "PhoBERT",
            "f1": 0.0,
            "throughput": 0.0,
            "costPerMillion": 0.0,
            "googleMatch": 0.0,
            "sampleSize": 0,
        },
        "siamese": {
            "name": "Siamese (mGTE)",
            "f1": 0.0,
            "throughput": 0.0,
            "costPerMillion": 0.0,
            "googleMatch": 0.0,
            "sampleSize": 0,
        },
        "llm": {
            "name": "LLM (Qwen3)",
            "f1": 0.0,
            "throughput": 0.0,
            "costPerMillion": 0.0,
            "googleMatch": 0.0,
            "sampleSize": 0,
        },
    }

    with db.connection() as conn:
        # 1) Detect available columns dynamically (because benchmark columns can be created later).
        col_rows = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :table
                """
            ),
            {"schema": target_schema, "table": target_table},
        ).fetchall()

        available_columns = {row[0] for row in col_rows}

        normalized_cols = {
            "phobert": "normalized_phobert",
            "siamese": "normalized_mgte",
            "llm": "normalized_llm",
        }

        # Ground-truth ưu tiên standard_address (benchmark), fallback address_standardized.
        ground_truth_col = None
        if "standard_address" in available_columns:
            ground_truth_col = "standard_address"
        elif "address_standardized" in available_columns:
            ground_truth_col = "address_standardized"

        # 2) Compute throughput from latest 1-hour processing by selected_ai_model.
        #    Throughput = processed_rows / 3600s.
        model_patterns = {
            "phobert": ["%phobert%"],
            "siamese": ["%mgte%", "%siamese%"],
            "llm": ["%llm%", "%qwen%"],
        }

        hourly_cost = {
            "phobert": 0.85,
            "siamese": 0.65,
            "llm": 5.50,
        }

        if "selected_ai_model" in available_columns and "updated_at" in available_columns:
            for model_key, patterns in model_patterns.items():
                conditions = " OR ".join(
                    [f"LOWER(selected_ai_model) LIKE LOWER(:p{i})" for i, _ in enumerate(patterns)]
                )
                params = {f"p{i}": pattern for i, pattern in enumerate(patterns)}

                count_row = conn.execute(
                    text(
                        f"""
                        SELECT COUNT(*)
                        FROM {target_schema}.{target_table}
                        WHERE updated_at >= NOW() - INTERVAL '1 hour'
                          AND selected_ai_model IS NOT NULL
                          AND ({conditions})
                        """
                    ),
                    params,
                ).first()

                processed_last_hour = int(count_row[0] or 0)
                throughput = processed_last_hour / 3600.0
                models[model_key]["throughput"] = round(throughput, 2)

                if throughput > 0:
                    # cost / 1M = (hourly_cost / throughput_per_sec) * 1_000_000 / 3600
                    cost_per_million = (hourly_cost[model_key] / throughput) * (1_000_000 / 3600)
                    models[model_key]["costPerMillion"] = round(cost_per_million, 2)

        # 3) Compute quality metrics from benchmark result columns if available.
        eval_ready = ground_truth_col is not None and all(
            col in available_columns for col in normalized_cols.values()
        )

        if eval_ready:
            rows = conn.execute(
                text(
                    f"""
                    SELECT {normalized_cols['phobert']} AS phobert_out,
                           {normalized_cols['siamese']} AS siamese_out,
                           {normalized_cols['llm']} AS llm_out,
                           {ground_truth_col} AS ground_truth
                    FROM {target_schema}.{target_table}
                    WHERE {ground_truth_col} IS NOT NULL
                      AND (
                        {normalized_cols['phobert']} IS NOT NULL OR
                        {normalized_cols['siamese']} IS NOT NULL OR
                        {normalized_cols['llm']} IS NOT NULL
                      )
                    ORDER BY updated_at DESC NULLS LAST
                    LIMIT 5000
                    """
                )
            ).mappings().all()

            for model_key, model_col in (("phobert", "phobert_out"), ("siamese", "siamese_out"), ("llm", "llm_out")):
                exact_hits = 0
                fuzzy_hits = 0
                total = 0

                for row in rows:
                    pred = row.get(model_col)
                    gt = row.get("ground_truth")
                    if not pred or not gt:
                        continue

                    total += 1
                    sim = _similarity_ratio(pred, gt)
                    if sim == 1.0:
                        exact_hits += 1
                    if sim >= 0.85:
                        fuzzy_hits += 1

                if total > 0:
                    exact_rate = exact_hits / total
                    fuzzy_rate = fuzzy_hits / total
                    # Proxy F1 from exact/fuzzy to keep KPI shape stable for UI benchmark.
                    if exact_rate + fuzzy_rate > 0:
                        f1_proxy = (2 * exact_rate * fuzzy_rate) / (exact_rate + fuzzy_rate)
                    else:
                        f1_proxy = 0.0

                    models[model_key]["f1"] = round(f1_proxy * 100, 2)
                    models[model_key]["googleMatch"] = round(fuzzy_rate * 100, 2)
                    models[model_key]["sampleSize"] = total

        # 4) Fallback cost if throughput unavailable (cold-start/no recent jobs).
        default_cost = {
            "phobert": 42.0,
            "siamese": 28.0,
            "llm": 260.0,
        }
        for key in models:
            if models[key]["costPerMillion"] <= 0:
                models[key]["costPerMillion"] = default_cost[key]

    return {
        "models": models,
        "meta": {
            "schema": f"{target_schema}.{target_table}",
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "note": "Realtime benchmark from DB aggregates; F1 is proxy from exact/fuzzy agreement with ground-truth column.",
        },
    }


@api_router.get("/benchmark/baselines")
def get_benchmark_baselines(db: Session = Depends(get_db)):
    """Return benchmark baselines stored in the database."""
    seed_training_metadata()
    rows = db.query(BenchmarkModelBaseline).order_by(BenchmarkModelBaseline.id.asc()).all()
    models = {
        row.model_key: {
            "name": row.model_name,
            "f1": float(row.f1 or 0.0),
            "throughput": float(row.throughput or 0.0),
            "costPerMillion": float(row.cost_per_million or 0.0),
            "googleMatch": float(row.google_match or 0.0),
            "sampleSize": int(row.sample_size or 0),
        }
        for row in rows
    }
    return {
        "models": models,
        "meta": {
            "schema": "ath.benchmark_model_baselines",
            "generatedAt": datetime.utcnow().isoformat() + "Z",
        },
    }


@api_router.post("/benchmark/trigger")
def trigger_benchmark_job(data: dict = None, current_user: str = Depends(get_current_user)):
    payload = data or {}
    config_path = payload.get("config_path", "app/ai/config.yaml")
    skip_llm = bool(payload.get("skip_llm", False))

    with benchmark_job_lock:
        if benchmark_job_state.get("status") == "running":
            return {
                "status": "running",
                "message": "Benchmark job is already running",
                "job": benchmark_job_state,
            }

        job_id = str(uuid4())
        benchmark_job_state.update({
            "jobId": job_id,
            "status": "running",
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "finishedAt": None,
            "configPath": config_path,
            "skipLLM": skip_llm,
            "exitCode": None,
            "error": None,
            "outputTail": None,
        })

    worker = threading.Thread(
        target=_run_benchmark_job,
        args=(job_id, config_path, skip_llm),
        daemon=True,
    )
    worker.start()

    return {
        "status": "accepted",
        "message": "Benchmark job started",
        "job": benchmark_job_state,
    }


@api_router.get("/training/history")
def get_training_history(db: Session = Depends(get_db)):
    """Return stored training history rows for the dashboard."""
    try:
        seed_training_metadata()
        rows = db.query(TrainingHistory).order_by(TrainingHistory.created_at.asc(), TrainingHistory.id.asc()).all()
        history = [
            {
                "version": row.version,
                "accuracy": float(row.accuracy or 0.0),
                "f1": float(row.f1_score or 0.0),
                "samples": int(row.samples_count or 0),
                "date": row.created_at.date().isoformat() if row.created_at else None,
                "loss": float(row.loss or 0.0),
                "notes": row.notes,
            }
            for row in rows
        ]
        return {"history": history, "meta": {"schema": "ath.training_history", "generatedAt": datetime.utcnow().isoformat() + "Z"}}
    except Exception as e:
        logger.warning(f"Training history fetch error (likely schema not yet created): {e}")
        return {"history": [], "meta": {"schema": "ath.training_history", "generatedAt": datetime.utcnow().isoformat() + "Z", "error": str(e)}}


@api_router.post("/training/history")
def create_training_history(data: dict = None, current_user: str = Depends(get_current_user)):
    """Persist a training history entry for the dashboard."""
    payload = data or {}
    row = TrainingHistory(
        version=str(payload.get("version", "unknown")),
        accuracy=float(payload.get("accuracy", 0.0)),
        f1_score=float(payload.get("f1", payload.get("f1_score", 0.0))),
        loss=float(payload.get("loss", 0.0)),
        samples_count=int(payload.get("samples", payload.get("samples_count", 0))),
        notes=payload.get("notes"),
    )

    db: Session = SessionLocal()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "status": "created",
            "history": {
                "version": row.version,
                "accuracy": float(row.accuracy or 0.0),
                "f1": float(row.f1_score or 0.0),
                "samples": int(row.samples_count or 0),
                "date": row.created_at.date().isoformat() if row.created_at else None,
                "loss": float(row.loss or 0.0),
                "notes": row.notes,
            },
        }
    finally:
        db.close()


@api_router.get("/benchmark/job")
def get_benchmark_job_status(current_user: str = Depends(get_current_user)):
    with benchmark_job_lock:
        return {"job": dict(benchmark_job_state)}

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


@api_router.get("/osm/preview")
def preview_osm_counts(db: Session = Depends(get_db)):
    return {
        "counts": osm_summary(db),
        "previewAt": datetime.utcnow().isoformat() + "Z",
    }


@api_router.post("/osm/trigger")
def trigger_osm_job(data: dict = None, current_user: str = Depends(get_current_user)):
    payload = data or {}
    limit_provinces = _normalize_int_value(payload.get("limit_provinces"), 63)
    target_total = _normalize_int_value(payload.get("target_total"), 5000000)

    with osm_job_lock:
        if osm_job_state.get("status") == "running":
            return {
                "status": "running",
                "message": "OSM job is already running",
                "job": osm_job_state,
            }

        job_id = str(uuid4())
        osm_job_state.update({
            "jobId": job_id,
            "status": "running",
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "finishedAt": None,
            "limitProvinces": limit_provinces,
            "targetTotal": target_total,
            "normalizedTargetTotal": target_total,
            "exitCode": None,
            "error": None,
            "outputTail": f"Normalized targetTotal: {target_total:,}",
        })

    worker = threading.Thread(
        target=_run_osm_job,
        args=(job_id, limit_provinces, target_total),
        daemon=True,
    )
    worker.start()

    return {
        "status": "accepted",
        "message": "OSM crawl job started",
        "job": osm_job_state,
    }


@api_router.get("/osm/job")
def get_osm_job_status(current_user: str = Depends(get_current_user)):
    with osm_job_lock:
        return {"job": dict(osm_job_state)}

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

# Note: CRUD routes merged into core admin endpoints.

# ── ADDRESS PARSER RESEARCH ENDPOINTS ──

@api_router.get("/parser/sample")
def get_parser_sample(db: Session = Depends(get_db)):
    """Lấy một mẫu địa chỉ ngẫu nhiên từ queue để nghiên cứu."""
    sample = _get_random_parser_sample(db)
    if not sample:
        raise HTTPException(status_code=404, detail="No samples found in queue")
    return _serialize_parser_sample(sample)


@api_router.post("/parser/analyze")
def analyze_parser_address(data: dict, db: Session = Depends(get_db)):
    """
    Phân tích địa chỉ bằng nhiều mô hình (Research Comparison).
    Hỗ trợ cả phân tích từ ID (trong DB) hoặc text thô.
    """
    sample_id = data.get("id")
    raw_text = data.get("raw_address")
    
    if sample_id:
        sample = db.query(AddressCleansingQueue).filter(AddressCleansingQueue.id == sample_id).first()
    elif raw_text:
        # Tạo sample giả lập nếu chỉ có text
        sample = AddressCleansingQueue(
            raw_address=raw_text,
            ward_name=data.get("ward_name"),
            district_name=data.get("district_name"),
            province_name=data.get("province_name")
        )
    else:
        raise HTTPException(status_code=400, detail="Missing id or raw_address")
    
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
        
    try:
        return _run_parser_research(sample)
    except Exception as e:
        logger.error(f"Parser Research Error: {e}\n{traceback.format_exc()}")
        # Fallback: Nếu model thật chưa load được (do thiếu GPU/RAM), trả về kết quả PreLabeler tối thiểu
        from app.ai.export_for_annotation import PreLabeler
        prelabeler_result = PreLabeler.predict(
            sample.raw_address,
            sample.ward_name,
            sample.district_name,
            sample.province_name
        )
        return {
            "sample": _serialize_parser_sample(sample) if sample_id else {"raw_address": raw_text},
            "analysis_input": sample.raw_address,
            "outputs": {
                "prelabeler": {
                    "mode": "rule_based_hybrid",
                    "result": prelabeler_result,
                    "entityCount": len(prelabeler_result),
                }
            },
            "error": str(e),
            "meta": {
                "corpusSize": 0,
                "evaluatedAt": datetime.utcnow().isoformat() + "Z",
                "note": "Running in fallback mode (PreLabeler only) due to inference engine error."
            }
        }

def _read_explorer_queue(db: Session, limit: int, q: str):
    try:
        query = db.query(AddressCleansingQueue)
        if q:
            query = query.filter(AddressCleansingQueue.raw_address.ilike(f"%{q}%"))
        
        samples = query.order_by(AddressCleansingQueue.id.desc()).limit(limit).all()
        
        return [
            {
                "id": s.id,
                "raw_address": s.raw_address,
                "ward_name": s.ward_name,
                "district_name": s.district_name,
                "province_name": s.province_name,
                "status": s.processing_status or "PENDING"
            }
            for s in samples
        ]
    except Exception as e:
        logger.warning(f"Explorer queue fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn prq.address_cleansing_queue: {str(e)}")


@api_router.get("/explorer/queue")
def get_explorer_queue(db: Session = Depends(get_db), limit: int = 100, q: str = ""):
    return _read_explorer_queue(db, limit, q)


@app.get("/explorer/queue")
def get_explorer_queue_root(db: Session = Depends(get_db), limit: int = 100, q: str = ""):
    return _read_explorer_queue(db, limit, q)

@api_router.get("/label-studio/tasks")
async def get_ls_tasks(current_user: str = Depends(get_current_user)):
    """Fetch tasks from Label Studio API."""
    ls_token = os.getenv("LABEL_STUDIO_API_TOKEN")
    ls_url = os.getenv("LABEL_STUDIO_URL", "https://label.nod.io.vn")
    project_id = os.getenv("LABEL_STUDIO_PROJECT_ID", "1")
    
    if not ls_token:
        logger.warning("LABEL_STUDIO_API_TOKEN not found in environment. Returning mock data.")
        return [
            {"id": 101, "data": {"address": "2695/7 Phạm Thế Hiển, P7, Q8, HCM"}, "created_at": "2026-04-28T10:00:00Z", "is_labeled": True, "project": project_id},
            {"id": 102, "data": {"address": "123 Lê Lợi, Bến Thành, Q1, HCM"}, "created_at": "2026-04-28T11:00:00Z", "is_labeled": False, "project": project_id},
            {"id": 103, "data": {"address": "456 Nguyễn Huệ, Q1, HCM"}, "created_at": "2026-04-29T00:15:00Z", "is_labeled": False, "project": project_id},
        ]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Note: Label Studio API uses "Token <key>" or "Bearer <key>"
            headers = {"Authorization": f"Token {ls_token}"}
            # API endpoint: /api/projects/{id}/tasks
            # See: https://labelstud.io/api#operation/api_projects_tasks_list
            response = await client.get(
                f"{ls_url.rstrip('/')}/api/projects/{project_id}/tasks",
                headers=headers,
                params={"page_size": 100}
            )
            
            if response.status_code != 200:
                logger.error(f"Label Studio returned {response.status_code}: {response.text}")
                return []
                
            tasks = response.json()
            # Normalize response if it's a paginated object
            if isinstance(tasks, dict) and "tasks" in tasks:
                tasks = tasks["tasks"]
            elif isinstance(tasks, dict) and "results" in tasks:
                tasks = tasks["results"]
                
            return tasks
    except Exception as e:
        logger.error(f"Error connecting to Label Studio: {e}")
        return []

# Register API router
api_router_v1 = APIRouter(prefix="/api/v1")
api_router_v1.include_router(api_router)
app.include_router(api_router, prefix="/api") # Match frontend API_BASE
app.include_router(api_router_v1) # Support /api/v1/*

if __name__ == "__main__":
    import uvicorn
    # Changed port to 8081 to match VPS setup (avoiding 8080 which might be used by Docker)
    uvicorn.run(app, host="0.0.0.0", port=8081)
