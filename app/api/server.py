from __future__ import annotations
from fastapi import FastAPI, Depends, Request, HTTPException, status, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session, aliased
from sqlalchemy import String, and_, or_, text, func
import os
import logging
import time
import re
import jwt
import sys

# Handle _lzma import with fallback for compatibility
try:
    import _lzma
except ImportError:
    from backports import lzma
    sys.modules['_lzma'] = lzma

import subprocess
import threading
import traceback
import httpx
import io
import tempfile
import zipfile
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
import random
import string
from types import SimpleNamespace
from app.core.database import SessionLocal, Province, District, Ward, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset, TrainingHistory, BenchmarkModelBaseline, AddressCleansingQueue, WardMapping, AuthUser, EmailVerification, SyncLog, UnitEdge, engine, seed_training_metadata
from app.services.scd_sync import get_unit_at_date, get_sync_summary
from app.services.auth import verify_password, create_access_token, get_password_hash, ALGORITHM, SECRET_KEY
from app.services.email_service import send_verification_email
from app.services.nso_sync import sync_full_nso, sync_province_nso, sync_logs
from app.services.nso_api import get_nso_provinces, get_nso_districts, get_nso_wards
from app.services.prelabeler_labeling_service import (
    first_expected_text,
    predictions_to_expected,
    enforce_admin_type_name,
    validate_expected_against_actual,
)
from app.api import schemas
from app.api.boundary import router as boundary_router
from app.api.spatial import router as spatial_router
from typing import Any, Dict, List, Optional, Union
import json

from app.core.logging_config import setup_logging
from app.core.config import Config  # noqa: F401 - import to trigger load_dotenv from .env
from app.core.cache import (
    cache_provinces_get, cache_provinces_set,
    cache_districts_get, cache_districts_set,
    cache_wards_get, cache_wards_set,
    cache_unit_get, cache_unit_set,
    cache_mapping_get, cache_mapping_set,
    invalidate_provinces, invalidate_districts, invalidate_wards,
    invalidate_ward_mapping, invalidate_all_admin,
    cache_health, get_redis,
)

# ── Logging Setup ──
logger = setup_logging()
logger = logging.getLogger("VNAI_Server")

app = FastAPI(
    title="VN Address Intelligence API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc"
)


@app.on_event("startup")
async def on_startup():
    """Khởi tạo database và nạp model AI trong background."""
    _ensure_auth_user_table()
    # Note: _ensure_prelabeler_testcases_table is already called at import time
    _start_background_model_loading()

# Use APIRouter for cleaner route management
api_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


class SendCodePayload(BaseModel):
    email: str

class RegisterPayload(BaseModel):
    username: str
    email: str
    password: str
    verification_code: str
    display_name: Optional[str] = None

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

batch_job_lock = threading.Lock()
batch_job_state = {
    "jobId": None,
    "status": "idle",
    "startedAt": None,
    "finishedAt": None,
    "processedCount": 0,
    "totalCount": 0,
    "throughput": 0,
    "exitCode": None,
    "error": None,
    "outputTail": None,
}

parser_runtime_lock = threading.Lock()
parser_runtime_bundle = None
parser_loading_state = {
    "status": "idle",       # idle | loading | ready | error
    "startedAt": None,
    "finishedAt": None,
    "errors": {},
    "loadedModels": [],
}


def _ensure_auth_user_table():
    # 1. Create tables if not exist
    AuthUser.__table__.create(bind=engine, checkfirst=True)
    EmailVerification.__table__.create(bind=engine, checkfirst=True)
    
    # 2. Add email column to auth_users if missing (for existing installations)
    try:
        with engine.connect() as conn:
            # PostgreSQL syntax to add column if not exists
            conn.execute(text("ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS email VARCHAR(150) UNIQUE"))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to auto-migrate auth_users table: {e}")


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


def _update_batch_job_state(**kwargs):
    with batch_job_lock:
        batch_job_state.update(kwargs)


def _run_batch_job(job_id: str, limit: int, method: str):
    project_root = Path(__file__).resolve().parents[2]
    # We can call the production_pipeline.py as a separate process to avoid GIL issues
    # and keep the server responsive.
    cmd = [
        sys.executable,
        "-m",
        "app.ai.production_pipeline",
        "--limit",
        str(limit),
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
                
                # Parse progress from log lines
                progress_match = re.search(r'Progress:\s*(\d+)/(\d+)', line)
                if progress_match:
                    processed = int(progress_match.group(1))
                    total = int(progress_match.group(2))
                    # Calculate throughput (simple estimation)
                    start_time = datetime.fromisoformat(batch_job_state["startedAt"].replace("Z", ""))
                    elapsed = max(1, (datetime.utcnow() - start_time).total_seconds())
                    throughput = processed / elapsed
                    _update_batch_job_state(
                        processedCount=processed,
                        totalCount=total,
                        throughput=throughput,
                        outputTail=output_tail
                    )
                else:
                    # Update the log tail for realtime feedback in UI
                    _update_batch_job_state(outputTail=output_tail)

        return_code = proc.wait()

        if return_code == 0:
            _update_batch_job_state(
                status="success",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                processedCount=batch_job_state.get("totalCount", 0),  # Set to total when complete
                error=None,
                outputTail=output_tail,
            )
        else:
            _update_batch_job_state(
                status="failed",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                error=f"Batch process exited with code {return_code}",
                outputTail=output_tail,
            )
    except Exception as exc:
        _update_batch_job_state(
            status="failed",
            finishedAt=datetime.utcnow().isoformat() + "Z",
            exitCode=-1,
            error=f"{exc}\n{traceback.format_exc()}",
            outputTail=None,
        )


def _run_osm_job(job_id: str, limit_provinces: int, target_total: int):
    project_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "app.main",
        "osm:fetch",
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


def _queue_sample_columns() -> tuple:
    return (
        AddressCleansingQueue.id,
        AddressCleansingQueue.raw_address,
        AddressCleansingQueue.street_address,
        AddressCleansingQueue.ward_name,
        AddressCleansingQueue.district_name,
        AddressCleansingQueue.province_name,
        AddressCleansingQueue.address_standardized,
        AddressCleansingQueue.selected_ai_model,
        AddressCleansingQueue.processing_status,
        AddressCleansingQueue.processing_method,
        AddressCleansingQueue.updated_at,
    )


def _to_queue_sample(row: object) -> Optional[SimpleNamespace]:
    if row is None:
        return None
    if hasattr(row, "_mapping"):
        return SimpleNamespace(**dict(row._mapping))
    if isinstance(row, dict):
        return SimpleNamespace(**row)
    return row


def _serialize_parser_sample(sample: Union[AddressCleansingQueue, SimpleNamespace, dict]) -> dict:
    getter = sample.get if isinstance(sample, dict) else lambda k, d=None: getattr(sample, k, d)
    return {
        "id": getter("id"),
        "raw_address": getter("raw_address"),
        "street_address": getter("street_address"),
        "ward_name": getter("ward_name"),
        "district_name": getter("district_name"),
        "province_name": getter("province_name"),
        "address_standardized": getter("address_standardized"),
        "selected_ai_model": getter("selected_ai_model"),
        "processing_status": getter("processing_status"),
        "processing_method": getter("processing_method"),
        "updated_at": getter("updated_at").isoformat() + "Z" if getter("updated_at") else None,
    }


def _load_parser_corpus(db: Session) -> List[str]:
    """
    Load corpus với priority hierarchy:
    1. prq.ground_truth (new ground truth data)
    2. prq.address_clean_corpus (clean corpus)
    3. prq.address_cleansing_queue.address_standardized (legacy)
    4. Administrative hierarchy (fallback)
    """
    try:
        # Try loading from ground truth service first
        from app.services.ground_truth_service import GroundTruthService
        
        gt_service = GroundTruthService(db)
        corpus = gt_service.get_corpus_addresses(
            limit=100000,
            min_quality_score=0.7,
            source_systems=['TYPESENSE', 'GOOGLE']
        )
        
        if len(corpus) > 100:  # Sufficient corpus size
            logger.info("Using ground truth corpus with %d addresses", len(corpus))
            return corpus
            
    except Exception as e:
        logger.warning("Failed to load from ground truth service: %s", e)
    
    try:
        # Try loading from clean corpus table
        from sqlalchemy import text
        
        clean_corpus_query = text("""
            SELECT standardized_address 
            FROM prq.address_clean_corpus
            WHERE is_active = true 
              AND admin_epoch = '2025'
              AND quality_score >= 0.7
              AND LENGTH(standardized_address) > 5
            ORDER BY quality_score DESC, usage_count DESC
            LIMIT 100000
        """)
        
        clean_corpus_result = db.execute(clean_corpus_query).fetchall()
        if clean_corpus_result:
            corpus = [row[0] for row in clean_corpus_result if row[0]]
            if len(corpus) > 100:  # Sufficient corpus size
                logger.info("Using clean corpus with %d addresses", len(corpus))
                return corpus
                
    except Exception as e:
        logger.warning("Failed to load from address_clean_corpus: %s", e)
    
    # Fallback to legacy queue standardized addresses
    try:
        standardized_rows = (
            db.query(AddressCleansingQueue.address_standardized)
            .filter(AddressCleansingQueue.address_standardized.isnot(None))
            .filter(func.length(AddressCleansingQueue.address_standardized) > 10)
            .distinct()
            .limit(100000)
            .all()
        )
        corpus = [row[0] for row in standardized_rows if row and row[0]]

        if len(corpus) > 50:  # Minimum viable corpus
            logger.info("Using queue standardized corpus with %d addresses", len(corpus))
            return corpus
            
    except Exception as e:
        logger.warning("Failed to load from queue standardized: %s", e)

    # Final fallback to administrative hierarchy
    try:
        hierarchy_rows = (
            db.query(Ward.ward_name, District.district_name, Province.province_name)
            .join(District, and_(Ward.district_id == District.district_id, Ward.admin_version == District.admin_version))
            .join(Province, and_(District.province_id == Province.province_id, District.admin_version == Province.admin_version))
            .filter(Ward.is_deleted == False, District.is_deleted == False, Province.is_deleted == False)
            .limit(100000)
            .all()
        )
        corpus = [f"{ward}, {district}, {province}" for ward, district, province in hierarchy_rows if ward and district and province]
        logger.info("Using administrative hierarchy corpus with %d addresses", len(corpus))
        return corpus
        
    except Exception as e:
        logger.error("Failed to load any corpus: %s", e)
        return []


def _build_parser_runtime_bundle() -> dict:
    """Load AI models for parser research. Handles errors gracefully."""
    global parser_loading_state
    from app.ai.models import LLMQwen3, PhoBERTSiamese, SiameseMGTE
    from app.ai.export_for_annotation import PreLabeler

    parser_loading_state.update({
        "status": "loading",
        "startedAt": datetime.utcnow().isoformat() + "Z",
        "finishedAt": None,
        "errors": {},
        "loadedModels": [],
    })

    bundle = {
        "phobert": None,
        "mgte": None,
        "llm": None,
        "address_ner": None,
        "address_ner_model_id": None,
        "prelabeler": PreLabeler,
        "corpus": [],
        "errors": {}
    }

    try:
        import psutil
        mem = psutil.virtual_memory()
        logger.info(f"System Memory before loading models: {mem.available / (1024**3):.2f}GB available of {mem.total / (1024**3):.2f}GB total")
    except ImportError:
        logger.warning("psutil not installed, skipping memory check.")

    try:
        with SessionLocal() as db:
            bundle["corpus"] = _load_parser_corpus(db)
    except Exception as e:
        logger.error(f"Failed to load parser corpus: {e}")
        bundle["errors"]["corpus"] = str(e)

    # Load PhoBERT
    try:
        logger.info("Loading PhoBERT model...")
        parser_loading_state["currentModel"] = "phobert"
        phobert = PhoBERTSiamese(model_name="vinai/phobert-base", device="auto")
        if bundle["corpus"]:
            logger.info(f"Encoding corpus with PhoBERT ({len(bundle['corpus'])} addresses)...")
            phobert.encode_corpus(bundle["corpus"])
        bundle["phobert"] = phobert
        parser_loading_state["loadedModels"].append("phobert")
        parser_loading_state["currentModel"] = None
        logger.info("PhoBERT model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load PhoBERT: {e}")
        bundle["errors"]["phobert"] = str(e)
        parser_loading_state["errors"]["phobert"] = str(e)
        parser_loading_state["currentModel"] = None

    # Load mGTE
    try:
        logger.info("Loading mGTE model...")
        parser_loading_state["currentModel"] = "mgte"
        mgte = SiameseMGTE(model_name="Alibaba-NLP/gte-multilingual-base", device="auto")
        if bundle["corpus"]:
            logger.info(f"Encoding corpus with mGTE ({len(bundle['corpus'])} addresses)...")
            mgte.encode_corpus(bundle["corpus"])
        bundle["mgte"] = mgte
        parser_loading_state["loadedModels"].append("mgte")
        parser_loading_state["currentModel"] = None
        logger.info("mGTE model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load mGTE: {e}")
        bundle["errors"]["mgte"] = str(e)
        parser_loading_state["errors"]["mgte"] = str(e)
        parser_loading_state["currentModel"] = None

    # Load LLM (Qwen2.5-1.5B-Instruct with quantization for speed)
    try:
        logger.info("Loading LLM model (this may take 2-3 minutes)...")
        parser_loading_state["currentModel"] = "llm"
        llm = LLMQwen3(model_name="Qwen/Qwen2.5-1.5B-Instruct", use_quantization=True, device="auto")
        bundle["llm"] = llm
        parser_loading_state["loadedModels"].append("llm")
        parser_loading_state["currentModel"] = None
        logger.info("LLM Qwen model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load LLM: {e}")
        bundle["errors"]["llm"] = str(e)
        parser_loading_state["errors"]["llm"] = str(e)
        parser_loading_state["currentModel"] = None

    # AddressNER — cùng quy tắc chọn model như production_pipeline / NER_MODEL_ID
    try:
        from app.ai.models.ner_model import AddressNER, resolve_ner_model_path

        ner_path = resolve_ner_model_path()
        bundle["address_ner_model_id"] = ner_path
        logger.info("Loading AddressNER for parser (%s)...", ner_path)
        parser_loading_state["currentModel"] = "address_ner"
        address_ner = AddressNER(model_path=ner_path)
        bundle["address_ner"] = address_ner
        parser_loading_state["loadedModels"].append("address_ner")
        if not address_ner.ner_pipeline:
            _ner_warn = "Transformer NER không khả dụng — chỉ regex fallback"
            bundle["errors"]["address_ner"] = _ner_warn
            parser_loading_state["errors"]["address_ner"] = _ner_warn
        parser_loading_state["currentModel"] = None
        logger.info("AddressNER for parser ready (transformer=%s)", bool(address_ner.ner_pipeline))
    except Exception as e:
        logger.error("Failed to load AddressNER for parser: %s", e)
        bundle["errors"]["address_ner"] = str(e)
        parser_loading_state["errors"]["address_ner"] = str(e)
        parser_loading_state["currentModel"] = None

    has_errors = bool(bundle["errors"])
    parser_loading_state.update({
        "status": "error" if not parser_loading_state["loadedModels"] and has_errors else "ready",
        "finishedAt": datetime.utcnow().isoformat() + "Z",
    })

    return bundle


def _get_parser_runtime_bundle() -> dict:
    global parser_runtime_bundle
    with parser_runtime_lock:
        if parser_runtime_bundle is None:
            parser_runtime_bundle = _build_parser_runtime_bundle()
        return parser_runtime_bundle


def _start_background_model_loading():
    """Trigger model loading in a background thread at server startup."""
    global parser_runtime_bundle, parser_loading_state
    with parser_runtime_lock:
        if parser_runtime_bundle is not None or parser_loading_state["status"] == "loading":
            return
        parser_loading_state["status"] = "loading"

    def _load():
        global parser_runtime_bundle
        bundle = _build_parser_runtime_bundle()
        with parser_runtime_lock:
            parser_runtime_bundle = bundle
        logger.info(f"Background model loading complete. Loaded: {parser_loading_state['loadedModels']}")

    t = threading.Thread(target=_load, daemon=True, name="model-loader")
    t.start()
    logger.info("Background AI model loading started")


def _get_random_parser_sample(db: Session) -> AddressCleansingQueue:
    row = (
        db.query(*_queue_sample_columns())
        .filter(AddressCleansingQueue.raw_address.isnot(None))
        .order_by(text("random()"))
        .first()
    )
    return _to_queue_sample(row)


def _run_parser_research(sample: AddressCleansingQueue, target_model: Optional[str] = None) -> dict:
    bundle = _get_parser_runtime_bundle()
    raw_address = sample.raw_address or ""
    ward_name = sample.ward_name
    district_name = sample.district_name
    province_name = sample.province_name

    def _build_llm_candidates() -> List[str]:
        import numpy as np
        corpus = bundle.get("corpus") or []
        mgte = bundle.get("mgte")
        corpus_emb = getattr(mgte, "_corpus_emb", None)
        if not corpus or mgte is None or corpus_emb is None or corpus_emb.shape[0] == 0:
            return []
        try:
            q_emb = mgte.model.encode([raw_address], normalize_embeddings=True, convert_to_numpy=True)[0]
            scores = corpus_emb @ q_emb
            top_idx = np.argsort(scores)[::-1][:5]
            return [corpus[int(i)] for i in top_idx]
        except Exception:
            return []

    outputs = {}

    # 1. PreLabeler (Always available)
    if not target_model or target_model == "prelabeler":
        try:
            outputs["prelabeler"] = {
                "mode": "rule_based_hybrid",
                "result": bundle["prelabeler"].predict(raw_address, ward_name, district_name, province_name),
                "entityCount": 0,
            }
            outputs["prelabeler"]["entityCount"] = len(outputs["prelabeler"]["result"])
        except Exception as e:
            outputs["prelabeler"] = {"error": str(e)}

    # 1b. AddressNER (HF / PhoBERT fine-tune / regex) — đồng bộ production
    if not target_model or target_model == "address_ner":
        ner_inst = bundle.get("address_ner")
        model_id = bundle.get("address_ner_model_id")
        if ner_inst:
            try:
                t0 = time.perf_counter()
                result_dict = ner_inst.extract(raw_address)
                lat_ms = (time.perf_counter() - t0) * 1000
                outputs["address_ner"] = {
                    "mode": "address_ner",
                    "model_id": model_id,
                    "result": result_dict,
                    "entityCount": len([k for k, v in (result_dict or {}).items() if v]),
                    "latencyMs": round(lat_ms, 2),
                    "deep_ner_active": bool(getattr(ner_inst, "ner_pipeline", None)),
                }
            except Exception as e:
                outputs["address_ner"] = {"error": str(e)}
        else:
            outputs["address_ner"] = {
                "status": "Not loaded",
                "error": bundle.get("errors", {}).get("address_ner", "AddressNER not initialized"),
            }

    # 2. PhoBERT
    if not target_model or target_model == "phobert":
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
    if not target_model or target_model == "mgte":
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

    # 4. LLM — run in thread with hard timeout to avoid Cloudflare 524
    _LLM_TIMEOUT_SEC = 55  # Cloudflare kills at 100s; give plenty of margin
    if not target_model or target_model == "llm":
        if bundle.get("llm"):
            try:
                candidates = _build_llm_candidates()
                llm_instance = bundle["llm"]

                def _llm_task():
                    return llm_instance.normalize(raw_address, candidates)

                with ThreadPoolExecutor(max_workers=1) as _ex:
                    _future = _ex.submit(_llm_task)
                    try:
                        norm, score, lat = _future.result(timeout=_LLM_TIMEOUT_SEC)
                        if isinstance(norm, str):
                            norm_str = norm
                        elif isinstance(norm, dict):
                            norm_str = str(norm.get("full_address") or raw_address)
                        else:
                            norm_str = str(norm)
                        outputs["llm"] = {
                            "mode": "qwen2.5_llm",
                            "normalizedAddress": norm_str,
                            "score": round(float(score), 4),
                            "latencyMs": round(float(lat), 2),
                        }
                    except TimeoutError:
                        logger.warning(f"LLM timed out after {_LLM_TIMEOUT_SEC}s for: {raw_address[:60]}")
                        outputs["llm"] = {
                            "error": f"LLM timeout sau {_LLM_TIMEOUT_SEC}s — model quá chậm trên hardware hiện tại",
                            "status": "timeout",
                        }
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"LLM normalize error:\n{tb}")
                outputs["llm"] = {"error": str(e)}
        else:
            outputs["llm"] = {"status": "Not loaded", "error": bundle["errors"].get("llm")}

    # Compute ACS using the best available semantic score
    acs_data: dict = {}
    try:
        from app.ai.acs_calculator import ACSCalculator
        from app.ai.epoch_detector import EpochDetector

        best_sem_score = 0.0
        best_std_addr  = raw_address
        for key in ("mgte", "phobert", "llm"):
            out = outputs.get(key, {})
            if "score" in out and out["score"] > best_sem_score:
                best_sem_score = out["score"]
                best_std_addr  = out.get("normalizedAddress", raw_address) or raw_address

        acs_calc   = ACSCalculator(db_session=None)
        epoch_det  = EpochDetector(db_session=None)
        epoch_res  = epoch_det.detect(raw_address)
        admin_ver  = 1 if epoch_res.epoch == "PRE_2025" else 2

        acs_comp = acs_calc.compute(
            raw_address=raw_address,
            standardized_address=best_std_addr,
            semantic_score=best_sem_score,
            admin_version=admin_ver,
        )
        acs_data = {
            "acs_score":    acs_comp.acs_score,
            "acs_decision": acs_comp.acs_decision,
            "s_text":       acs_comp.s_text,
            "s_sem":        acs_comp.s_sem,
            "v_hierarchy":  acs_comp.v_hierarchy,
            "v_temporal":   acs_comp.v_temporal,
            "address_epoch": epoch_res.epoch,
            "epoch_confidence": epoch_res.confidence,
        }
    except Exception as _acs_err:
        logger.debug("ACS compute skipped: %s", _acs_err)

    return {
        "sample": _serialize_parser_sample(sample),
        "analysis_input": raw_address,
        "outputs": outputs,
        "acs": acs_data,
        "meta": {
            "corpusSize": len(bundle.get("corpus") or []),
            "evaluatedAt": datetime.utcnow().isoformat() + "Z",
            "nerModelId": bundle.get("address_ner_model_id"),
            "note": None,
        },
    }

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Visitor Tracking & Kibana Logging Middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Extract client IP
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0] if forwarded else (request.client.host if request.client else "unknown")
    
    # 1. Visitor Tracking (Internal stats)
    if not request.url.path.startswith(("/ui", "/favicon.ico")):
        stats_tracker.track(ip)
        
    response = await call_next(request)
    
    # 2. Kibana/Logstash Logging
    if Config.KIBANA_LOG_ENABLED:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": ip,
            "user_agent": request.headers.get("User-Agent", "unknown"),
        }
        # Log detail for Kibana indexing
        logger.info(
            f"HTTP {request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)",
            extra=log_data
        )
        
    return response

# Serve UI static files
app.mount("/ui", StaticFiles(directory="ui"), name="ui")
app.mount("/pages", StaticFiles(directory="ui/pages"), name="pages")

@app.get("/", tags=["Giao diện người dùng"], summary="Trang chủ")
@app.get("/index.html", tags=["Giao diện người dùng"], include_in_schema=False)
def read_root():
    """Trả về trang Dashboard chính của hệ thống."""
    return FileResponse('ui/index.html')

@app.get("/login.html", tags=["Giao diện người dùng"], summary="Trang đăng nhập")
def read_login():
    """Trả về trang đăng nhập hệ thống."""
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

@api_router.get("/health", tags=["Hệ thống"], summary="Kiểm tra trạng thái hệ thống")
def health_check():
    """Trả về trạng thái hoạt động của API và thời gian máy chủ hiện tại."""
    return {"status": "ok", "time": time.time()}


@api_router.get("/config/ner-labels", tags=["Hệ thống"], summary="Danh sách nhãn NER cho UI")
def get_ner_labels_for_ui():
    """Trả về `NER_LABELS` từ `app/ai/constants.py` — nguồn duy nhất cho SPA và Label Studio export."""
    from app.ai.constants import NER_LABELS

    return {"labels": list(NER_LABELS)}

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

@api_router.get("/provinces", tags=["Đơn vị hành chính"], summary="Lấy danh sách Tỉnh/Thành phố")
def get_provinces(version: int = Query(1), db: Session = Depends(get_db)):
    """
    Lấy toàn bộ danh sách tỉnh/thành phố.
    - **version**: 1 (Dữ liệu cũ), 2 (Dữ liệu mới quy chuẩn).
    """
    cached = cache_provinces_get(version)
    if cached is not None:
        return cached
    query = db.query(
        Province.row_id,
        Province.province_id,
        Province.area_id,
        Province.bonus_area_id,
        Province.country_id,
        Province.province_no,
        Province.province_name,
        Province.type_name,
        Province.is_default,
        Province.created_user,
        Province.created_date,
        Province.updated_user,
        Province.updated_date,
        Province.is_deleted,
        Province.province_name_en,
        Province.old_id,
        Province.served_radius,
        Province.north_pole_lat,
        Province.north_pole_lng,
        Province.east_pole_lat,
        Province.east_pole_lng,
        Province.south_pole_lat,
        Province.south_pole_lng,
        Province.west_pole_lat,
        Province.west_pole_lng,
        Province.admin_version,
        Province.population,
        Province.area_km2,
        Province.decision_number,
        Province.decision_date,
        Province.notes,
    ).filter(Province.admin_version == version)
    if version == 2:
        query = query.filter(Province.is_deleted == False)
    rows = [dict(r._mapping) for r in query.order_by(Province.province_name).all()]
    cache_provinces_set(version, rows)
    return rows

@api_router.get("/provinces/{province_id}")
def get_provinces_by_path(province_id: int, version: Optional[int] = 1, db: Session = Depends(get_db)):
    """Fetch a single province by ID and version."""
    cached = cache_unit_get("province", version, province_id)
    if cached is not None:
        return cached
    row = db.query(
        Province.row_id,
        Province.province_id,
        Province.area_id,
        Province.bonus_area_id,
        Province.country_id,
        Province.province_no,
        Province.province_name,
        Province.type_name,
        Province.is_default,
        Province.created_user,
        Province.created_date,
        Province.updated_user,
        Province.updated_date,
        Province.is_deleted,
        Province.province_name_en,
        Province.old_id,
        Province.served_radius,
        Province.north_pole_lat,
        Province.north_pole_lng,
        Province.east_pole_lat,
        Province.east_pole_lng,
        Province.south_pole_lat,
        Province.south_pole_lng,
        Province.west_pole_lat,
        Province.west_pole_lng,
        Province.admin_version,
        Province.population,
        Province.area_km2,
        Province.decision_number,
        Province.decision_date,
        Province.notes,
    ).filter(Province.province_id == province_id, Province.admin_version == version).first()
    if row:
        row = dict(row._mapping)
    if row:
        cache_unit_set("province", version, province_id, row)
    return row

@api_router.get("/districts", tags=["Đơn vị hành chính"], summary="Lấy danh sách Quận/Huyện")
def get_districts(province_id: Optional[int] = None, district_id: Optional[int] = None, version: int = Query(1), db: Session = Depends(get_db)):
    """
    Lấy danh sách quận/huyện theo bộ lọc.
    - **province_id**: Lọc theo mã tỉnh.
    - **district_id**: Lấy chính xác 1 huyện theo mã.
    - **version**: 1 hoặc 2.
    """
    if district_id is None:
        cached = cache_districts_get(version, province_id)
        if cached is not None:
            return cached
    query = db.query(
        District.row_id,
        District.district_id,
        District.province_id,
        District.district_no,
        District.district_name,
        District.type_name,
        District.location,
        District.is_default,
        District.created_user,
        District.created_date,
        District.updated_user,
        District.updated_date,
        District.is_deleted,
        District.district_name_en,
        District.old_id,
        District.sfdc_id,
        District.is_active,
        District.type_name_en,
        District.admin_version,
        District.population,
        District.area_km2,
        District.decision_number,
        District.decision_date,
        District.notes,
    ).filter(District.admin_version == version)
    if version == 2:
        query = query.filter(District.is_deleted == False)
    if province_id:
        query = query.filter(District.province_id == province_id)
    if district_id:
        query = query.filter(District.district_id == district_id)
    rows = [dict(r._mapping) for r in query.order_by(District.district_name).all()]
    if district_id is None:
        cache_districts_set(version, province_id, rows)
    return rows

@api_router.get("/districts/{province_id}")
def get_districts_by_path(province_id: int, version: int = Query(1), db: Session = Depends(get_db)):
    """Legacy support for path-based district lookup."""
    return get_districts(province_id=province_id, version=version, db=db)

@api_router.get("/wards", tags=["Đơn vị hành chính"], summary="Lấy danh sách Phường/Xã")
def get_wards(district_id: Optional[int] = None, ward_id: Optional[int] = None, version: int = Query(1), db: Session = Depends(get_db)):
    """
    Lấy danh sách phường/xã theo bộ lọc.
    - **district_id**: Lọc theo mã quận/huyện.
    - **ward_id**: Lấy chính xác 1 xã theo mã.
    - **version**: 1 hoặc 2.
    """
    if ward_id is None:
        cached = cache_wards_get(version, district_id)
        if cached is not None:
            return cached
    query = db.query(
        Ward.row_id,
        Ward.ward_id,
        Ward.district_id,
        Ward.province_no,
        Ward.ward_no,
        Ward.ward_name,
        Ward.type_name,
        Ward.location,
        Ward.is_default,
        Ward.created_user,
        Ward.created_date,
        Ward.updated_user,
        Ward.updated_date,
        Ward.is_deleted,
        Ward.ward_name_en,
        Ward.old_id,
        Ward.is_active,
        Ward.type_name_en,
        Ward.admin_version,
        Ward.population,
        Ward.area_km2,
        Ward.decision_number,
        Ward.decision_date,
        Ward.notes,
    ).filter(Ward.admin_version == version)
    if version == 2:
        query = query.filter(Ward.is_deleted == False)
    if district_id:
        query = query.filter(Ward.district_id == district_id)
    if ward_id:
        query = query.filter(Ward.ward_id == ward_id)
    rows = [dict(r._mapping) for r in query.order_by(Ward.ward_name).all()]
    if ward_id is None:
        cache_wards_set(version, district_id, rows)
    return rows

@api_router.get("/wards/{district_id}")
def get_wards_by_path(district_id: int, version: int = Query(1), db: Session = Depends(get_db)):
    """Legacy support for path-based ward lookup."""
    return get_wards(district_id=district_id, version=version, db=db)

@api_router.get("/unit-details/{level}/{unit_id}", tags=["Đơn vị hành chính"], summary="Lấy chi tiết một đơn vị hành chính")
def get_unit_details(level: str, unit_id: int, version: Optional[int] = 1, db: Session = Depends(get_db)):
    """
    Lấy thông tin chi tiết của một Tỉnh, Huyện hoặc Xã.
    - **level**: 'province', 'district', hoặc 'ward'.
    - **unit_id**: Mã định danh của đơn vị.
    - **version**: Phiên bản dữ liệu (1 hoặc 2).
    """
    cached = cache_unit_get(level, version, unit_id)
    if cached is not None:
        return cached
    row = None
    if level == "province":
        query = db.query(
            Province.row_id,
            Province.province_id,
            Province.area_id,
            Province.bonus_area_id,
            Province.country_id,
            Province.province_no,
            Province.province_name,
            Province.type_name,
            Province.is_default,
            Province.created_user,
            Province.created_date,
            Province.updated_user,
            Province.updated_date,
            Province.is_deleted,
            Province.province_name_en,
            Province.old_id,
            Province.served_radius,
            Province.north_pole_lat,
            Province.north_pole_lng,
            Province.east_pole_lat,
            Province.east_pole_lng,
            Province.south_pole_lat,
            Province.south_pole_lng,
            Province.west_pole_lat,
            Province.west_pole_lng,
            Province.admin_version,
            Province.population,
            Province.area_km2,
            Province.decision_number,
            Province.decision_date,
            Province.notes,
        ).filter(Province.province_id == unit_id, Province.admin_version == version)
        if version == 2:
            query = query.filter(Province.is_deleted == False)
        row = query.first()
    elif level == "district":
        query = db.query(
            District.row_id,
            District.district_id,
            District.province_id,
            District.district_no,
            District.district_name,
            District.type_name,
            District.location,
            District.is_default,
            District.created_user,
            District.created_date,
            District.updated_user,
            District.updated_date,
            District.is_deleted,
            District.district_name_en,
            District.old_id,
            District.sfdc_id,
            District.is_active,
            District.type_name_en,
            District.admin_version,
            District.population,
            District.area_km2,
            District.decision_number,
            District.decision_date,
            District.notes,
        ).filter(District.district_id == unit_id, District.admin_version == version)
        if version == 2:
            query = query.filter(District.is_deleted == False)
        row = query.first()
    elif level == "ward":
        query = db.query(
            Ward.row_id,
            Ward.ward_id,
            Ward.district_id,
            Ward.province_no,
            Ward.ward_no,
            Ward.ward_name,
            Ward.type_name,
            Ward.location,
            Ward.is_default,
            Ward.created_user,
            Ward.created_date,
            Ward.updated_user,
            Ward.updated_date,
            Ward.is_deleted,
            Ward.ward_name_en,
            Ward.old_id,
            Ward.is_active,
            Ward.type_name_en,
            Ward.admin_version,
            Ward.population,
            Ward.area_km2,
            Ward.decision_number,
            Ward.decision_date,
            Ward.notes,
        ).filter(Ward.ward_id == unit_id, Ward.admin_version == version)
        if version == 2:
            query = query.filter(Ward.is_deleted == False)
        row = query.first()
    else:
        return {"error": "Invalid level"}
    if row:
        row = dict(row._mapping)
        cache_unit_set(level, version, unit_id, row)
    return row

@api_router.get("/lookup/mapping", tags=["Biến động địa giới"], summary="Tra cứu chuyển đổi ĐVHC (V1 sang V2)")
def lookup_mapping(
    query: str = None, 
    province_id: int = None,
    district_id: int = None,
    ward_id: int = None,
    version: int = None,
    db: Session = Depends(get_db)
):
    """
    Tra cứu lịch sử biến động địa giới hành chính (Chia tách, sáp nhập, đổi tên).
    Hỗ trợ tìm kiếm theo tên hoặc lọc theo mã đơn vị.
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
        WardMapping.district_id_old,
        WardMapping.district_id_new,
        WardMapping.updated_note,
        WardMapping.effective_date_from,
        WardMapping.effective_date_to,
        WardMapping.relationship_type,
        WardMapping.mapping_total,
        
        WardV1.ward_name.label("ward_name_old"),
        WardV2.ward_name.label("ward_name_new"),
        ProvV1.province_name.label("province_name_old"),
        ProvV2.province_name.label("province_name_new"),
        DistV1.district_name.label("district_name_old"),
        DistV2.district_name.label("district_name_new")
    ).outerjoin(
        WardV1, and_(WardV1.ward_id == WardMapping.ward_id_old, WardV1.admin_version == 1) 
    ).outerjoin(
        WardV2, and_(WardV2.ward_id == WardMapping.ward_id_new, WardV2.is_deleted == False, WardV2.admin_version == 2)
    ).outerjoin(
        DistV1, and_(DistV1.district_id == func.coalesce(WardV1.district_id, WardMapping.district_id_old), DistV1.admin_version == 1)
    ).outerjoin(
        DistV2, and_(DistV2.district_id == func.coalesce(WardV2.district_id, WardMapping.district_id_new), DistV2.is_deleted == False, DistV2.admin_version == 2)
    ).outerjoin(
        ProvV1, and_(ProvV1.province_id == func.coalesce(DistV1.province_id, WardMapping.province_id_old), ProvV1.admin_version == 1)
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
            filters.append(or_(WardMapping.district_id_old == district_id, WardV1.district_id == district_id, DistV1.district_id == district_id))
        elif version == 2:
            filters.append(or_(WardMapping.district_id_new == district_id, WardV2.district_id == district_id, DistV2.district_id == district_id))
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
            filters.append(or_(WardMapping.ward_id_old == ward_id, WardMapping.ward_id_new == ward_id))

    if query:
        q_clean = query.strip()
        filters.append(or_(
            WardV1.ward_name.ilike(f"%{q_clean}%"),
            WardV2.ward_name.ilike(f"%{q_clean}%"),
            DistV1.district_name.ilike(f"%{q_clean}%"),
            DistV2.district_name.ilike(f"%{q_clean}%"),
            ProvV1.province_name.ilike(f"%{q_clean}%"),
            ProvV2.province_name.ilike(f"%{q_clean}%"),
            WardMapping.updated_note.ilike(f"%{q_clean}%")
        ))

    if filters:
        base_query = base_query.filter(and_(*filters))
    
    try:
        results = base_query.order_by(WardMapping.effective_date_from.desc().nulls_last()).limit(500).all()
    except Exception as e:
        logger.error(f"Error in lookup_mapping query: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

    # 4. Format lại output và xử lý các case đặc biệt (-1)
    enriched_results = []
    for r in results:
        try:
            res = r._asdict()
            # Handle ward -1 (All wards)
            if res.get("ward_id_old") == -1:
                res["ward_name_old"] = "(Tất cả Xã)"
            
            # Ensure all name fields are not None for UI
            name_fields = [
                "ward_name_old", "ward_name_new", 
                "district_name_old", "district_name_new", 
                "province_name_old", "province_name_new"
            ]
            for field in name_fields:
                if res.get(field) is None:
                    res[field] = "N/A"
            
            # Ensure note is not None
            if res.get("updated_note") is None:
                res["updated_note"] = ""
                
            enriched_results.append(res)
        except Exception as e:
            logger.error(f"Error processing mapping result row: {e}")
            continue

    return enriched_results

@api_router.post("/sync/nso", tags=["Đồng bộ dữ liệu"], summary="Kích hoạt đồng bộ toàn bộ NSO")
def trigger_nso_sync(db: Session = Depends(get_db)):
    """Đồng bộ toàn bộ danh mục Tỉnh/Huyện/Xã từ server NSO (danhmuchanhchinh.nso.gov.vn)."""
    result = sync_full_nso(db)
    invalidate_all_admin()
    return result

@api_router.post("/sync/nso/province", tags=["Đồng bộ dữ liệu"], summary="Đồng bộ một Tỉnh từ NSO")
async def trigger_nso_province_sync(data: dict, db: Session = Depends(get_db)):
    """Đồng bộ một tỉnh cụ thể kèm các huyện/xã trực thuộc từ NSO."""
    p_code = data.get("code")
    p_name = data.get("name")
    if not p_code or not p_name:
        raise HTTPException(status_code=400, detail="Thiếu mã hoặc tên tỉnh")
    result = sync_province_nso(db, p_code, p_name)
    invalidate_provinces()
    invalidate_districts()
    invalidate_wards()
    invalidate_ward_mapping()
    return result

@api_router.get("/sync/nso/logs", tags=["Đồng bộ dữ liệu"], summary="Lấy nhật ký đồng bộ")
def get_sync_logs():
    """Truy xuất danh sách log đồng bộ thời gian thực."""
    return sync_logs

@api_router.delete("/sync/nso/logs", tags=["Đồng bộ dữ liệu"], summary="Xóa nhật ký đồng bộ")
def clear_sync_logs():
    """Xóa sạch bộ nhớ tạm chứa log đồng bộ."""
    sync_logs.clear()
    return {"status": "cleared"}

# ── NSO LIVE DATA ENDPOINTS ──

@api_router.get("/nso/provinces", tags=["Dữ liệu NSO (Live)"], summary="Lấy danh sách Tỉnh từ NSO")
def fetch_nso_provinces(date: str = None):
    """Tìm kiếm trực tiếp danh sách Tỉnh từ Web Service của NSO."""
    try:
        return get_nso_provinces(date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@api_router.get("/nso/districts", tags=["Dữ liệu NSO (Live)"], summary="Lấy danh sách Huyện từ NSO")
def fetch_nso_districts(province_no: str = "", province_name: str = "", date: str = None):
    """Tìm kiếm trực tiếp danh sách Quận/Huyện từ Web Service của NSO."""
    try:
        return get_nso_districts(province_no, province_name, date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@api_router.get("/nso/wards", tags=["Dữ liệu NSO (Live)"], summary="Lấy danh sách Xã từ NSO")
def fetch_nso_wards(province_no: str = "", province_name: str = "", district_no: str = "", district_name: str = "", date: str = None):
    """Tìm kiếm trực tiếp danh sách Phường/Xã từ Web Service của NSO."""
    try:
        return get_nso_wards(province_no, province_name, district_no, district_name, date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@api_router.post("/login", tags=["Xác thực hệ thống"], summary="Đăng nhập hệ thống")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Xác thực người dùng và trả về JWT Token.
    Hỗ trợ cả người dùng trong DB và tài khoản Admin cấu hình qua biến môi trường.
    """
    # Support DB-backed users first, then fall back to legacy admin env vars.
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "vnai@2026")
    db = SessionLocal()
    
    logger.info(f"Login attempt for user: {form_data.username}")
    try:
        try:
            _ensure_auth_user_table()
            user = db.query(AuthUser).filter(AuthUser.username == form_data.username, AuthUser.is_active == True).first()
        except Exception as db_error:
            logger.warning(f"Auth user lookup skipped due to DB error: {db_error}")
            user = None

        if user and verify_password(form_data.password, user.password_hash):
            logger.info(f"Login successful for DB user: {form_data.username}")
            access_token = create_access_token(data={"sub": form_data.username})
            return {"access_token": access_token, "token_type": "bearer"}

        if form_data.username == ADMIN_USER and form_data.password == ADMIN_PASS:
            logger.info(f"Login successful for fallback admin: {form_data.username}")
            access_token = create_access_token(data={"sub": form_data.username})
            return {"access_token": access_token, "token_type": "bearer"}

        logger.warning(f"Login failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        db.close()


@api_router.post("/register/send-code", tags=["Xác thực hệ thống"], summary="Gửi mã xác thực qua email")
async def send_reg_code(payload: SendCodePayload, db: Session = Depends(get_db)):
    """Gửi mã xác thực 6 chữ số tới email của người dùng."""
    _ensure_auth_user_table()
    email = payload.email.strip().lower()
    
    try:
        # 1. Check if email already exists
        existing_user = db.query(AuthUser).filter(AuthUser.email == email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email này đã được đăng ký")

        # 2. Generate 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        # 3. Store in DB
        verification = EmailVerification(
            email=email,
            code=code,
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()

        # 4. Send Email
        success = send_verification_email(email, code)
        if not success:
            logger.error(f"Email failed to send to {email}")
            # If email fails, we might want to tell the user
            raise HTTPException(status_code=500, detail="Không thể gửi email xác thực. Vui lòng kiểm tra lại cấu hình SMTP.")

        return {"message": "Mã xác thực đã được gửi tới email của bạn", "expires_in": "10 minutes"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_reg_code: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@api_router.post("/register", tags=["Xác thực hệ thống"], summary="Đăng ký tài khoản mới")
def register_user(payload: RegisterPayload, db: Session = Depends(get_db)):
    """Tạo tài khoản người dùng mới trong hệ thống sau khi xác thực email."""
    _ensure_auth_user_table()
    admin_user = os.getenv("ADMIN_USER", "admin")
    username = payload.username.strip()
    email = payload.email.strip().lower()
    password = payload.password.strip()
    verification_code = payload.verification_code.strip()
    display_name = (payload.display_name or "").strip() or None

    if len(username) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")
    if username == admin_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This username is reserved")

    # 1. Verify code
    verification = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.code == verification_code,
        EmailVerification.is_verified == False,
        EmailVerification.expires_at > datetime.utcnow()
    ).order_by(EmailVerification.created_at.desc()).first()

    if not verification:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác thực không hợp lệ hoặc đã hết hạn")

    # 2. Check existence again (to be safe)
    if db.query(AuthUser).filter(AuthUser.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    
    if db.query(AuthUser).filter(AuthUser.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    # 3. Create User
    user = AuthUser(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        display_name=display_name,
        role="user",
        is_active=True,
    )
    db.add(user)
    
    # Mark verification as used
    verification.is_verified = True
    
    db.commit()

    access_token = create_access_token(data={"sub": username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": username,
            "email": email,
            "display_name": display_name,
        },
    }


@api_router.post("/logout", tags=["Xác thực hệ thống"], summary="Đăng xuất")
def logout(current_user: str = Depends(get_current_user)):
    """Đăng xuất người dùng hiện tại."""
    return {"message": "Logged out", "user": current_user}

@api_router.get("/stats", tags=["Thống kê hệ thống"], summary="Tổng quan số liệu hệ thống")
def get_stats(db: Session = Depends(get_db)):
    """Trả về số lượng bản ghi tổng hợp của tất cả các bảng chính (Admin, OSM, AI) và thống kê khách truy cập."""
    """Returns absolute counts and metadata for all tables. Robust version."""
    def safe_count(model):
        try:
            return db.query(func.count()).select_from(model).scalar() or 0
        except Exception as e:
            logger.error(f"Stats Error: {e}")
            db.rollback()
            return 0

    return {
        "master": {
            "provinces": safe_count(Province),
            "districts": safe_count(District),
            "wards": safe_count(Ward),
            "mappings": safe_count(WardMapping)
        },
        "osm": {
            "total": safe_count(OSMRawEntity),
            "streets": safe_count(OSMStreet),
            "buildings": safe_count(OSMBuilding),
            "pois": safe_count(OSMPoi),
        },
        "ai": {
            "training_samples": safe_count(TrainingDataset),
            "cleansing_queue": safe_count(AddressCleansingQueue),
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


@api_router.get("/benchmark/realtime", tags=["Huấn luyện & Benchmark AI"], summary="Benchmark thời gian thực")
def get_benchmark_realtime(db: Session = Depends(get_db)):
    """
    Tính toán và trả về các chỉ số hiệu năng (F1, Throughput, Cost) thời gian thực của các mô hình AI 
    dựa trên dữ liệu xử lý gần nhất trong Database.
    """
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


@api_router.get("/benchmark/baselines", tags=["Huấn luyện & Benchmark AI"], summary="Lấy thông số cơ sở (Baselines)")
def get_benchmark_baselines(db: Session = Depends(get_db)):
    """Trả về các thông số cơ sở (Accuracy, Speed, Cost) của các phiên bản mô hình AI đã lưu trong DB."""
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


@api_router.post("/benchmark/trigger", tags=["Huấn luyện & Benchmark AI"], summary="Kích hoạt tiến trình Benchmark")
def trigger_benchmark_job(data: dict = None, current_user: str = Depends(get_current_user)):
    """Kích hoạt một tiến trình đánh giá (Benchmark) mô hình AI chạy ngầm trên server."""
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


@api_router.get("/training/history", tags=["Huấn luyện & Benchmark AI"], summary="Lấy lịch sử huấn luyện")
def get_training_history(db: Session = Depends(get_db)):
    """Truy xuất lịch sử các phiên bản mô hình AI đã được huấn luyện."""
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


@api_router.get("/benchmark/job", tags=["Huấn luyện & Benchmark AI"], summary="Trạng thái tiến trình Benchmark")
def get_benchmark_job_status(current_user: str = Depends(get_current_user)):
    """Lấy trạng thái hiện tại (đang chạy, hoàn thành, lỗi) của tiến trình Benchmark."""
    with benchmark_job_lock:
        return {"job": dict(benchmark_job_state)}

@api_router.get("/visitors", tags=["Thống kê hệ thống"], summary="Thống kê khách truy cập")
def get_visitor_stats():
    """Trả về số lượng truy cập tổng, IP duy nhất và số người đang online."""
    return {
        "total": stats_tracker.total_visits,
        "unique": len(stats_tracker.unique_ips),
        "online": stats_tracker.get_online_count()
    }

@api_router.get("/admin-v2/provinces", tags=["Đơn vị hành chính"], summary="Danh sách tỉnh phiên bản v2")
def list_provinces_v2(db: Session = Depends(get_db)):
    """Lấy danh sách toàn bộ các tỉnh thành thuộc phiên bản quản lý mới (v2)."""
    provinces = db.query(
        Province.row_id,
        Province.province_id,
        Province.area_id,
        Province.bonus_area_id,
        Province.country_id,
        Province.province_no,
        Province.province_name,
        Province.type_name,
        Province.is_default,
        Province.created_user,
        Province.created_date,
        Province.updated_user,
        Province.updated_date,
        Province.is_deleted,
        Province.province_name_en,
        Province.old_id,
        Province.served_radius,
        Province.north_pole_lat,
        Province.north_pole_lng,
        Province.east_pole_lat,
        Province.east_pole_lng,
        Province.south_pole_lat,
        Province.south_pole_lng,
        Province.west_pole_lat,
        Province.west_pole_lng,
        Province.admin_version,
        Province.population,
        Province.area_km2,
        Province.decision_number,
        Province.decision_date,
        Province.notes,
    ).filter(Province.admin_version == 2).all()
    provinces = [dict(r._mapping) for r in provinces]
    return provinces

@api_router.get("/osm/summary", tags=["Dữ liệu OpenStreetMap"], summary="Tổng quan dữ liệu thực địa (OSM)")
def osm_summary(db: Session = Depends(get_db)):
    """Trả về số lượng Đường, Nhà và POI đã thu thập được từ OpenStreetMap."""
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


@api_router.post("/osm/trigger", tags=["Dữ liệu OpenStreetMap"], summary="Kích hoạt thu thập OSM")
def trigger_osm_job(data: dict = None, current_user: str = Depends(get_current_user)):
    """Kích hoạt tiến trình thu thập dữ liệu từ Overpass API (OSM) cho các tỉnh thành."""
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


@api_router.post("/batch/trigger", tags=["Xử lý hàng loạt"], summary="Kích hoạt chuẩn hóa hàng loạt")
def trigger_batch_job(data: dict = None, current_user: str = Depends(get_current_user)):
    """Đưa các địa chỉ thô vào hàng đợi để chuẩn hóa tự động bằng AI theo lô lớn."""
    payload = data or {}
    limit = _normalize_int_value(payload.get("batch_size"), 1000)
    method = payload.get("method", "hybrid")

    with batch_job_lock:
        if batch_job_state.get("status") == "running":
            return {
                "status": "running",
                "message": "Batch job is already running",
                "job": batch_job_state,
            }

        job_id = str(uuid4())
        batch_job_state.update({
            "jobId": job_id,
            "status": "running",
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "finishedAt": None,
            "totalCount": limit,
            "processedCount": 0,
            "throughput": 0,
            "exitCode": None,
            "error": None,
            "outputTail": f"Starting batch processing for {limit} records using {method} method...",
        })

    worker = threading.Thread(
        target=_run_batch_job,
        args=(job_id, limit, method),
        daemon=True,
    )
    worker.start()

    return {
        "status": "accepted",
        "message": "Batch processing job started",
        "job": batch_job_state,
    }


@api_router.get("/batch/job")
def get_batch_job_status(current_user: str = Depends(get_current_user)):
    with batch_job_lock:
        return {"job": dict(batch_job_state)}

@api_router.get("/training/samples")
def training_samples(db: Session = Depends(get_db)):
    """Return top 20 training records."""
    samples = db.query(TrainingDataset).limit(20).all()
    return samples

@api_router.get("/enrichment/summary", tags=["Đơn vị hành chính"], summary="Thống kê dữ liệu làm giàu (Enrichment)")
def enrichment_summary(db: Session = Depends(get_db)):
    """Trả về số lượng Tỉnh và Xã đã được bổ sung thông tin chi tiết (Quyết định thành lập, Ghi chú)."""
    enriched_provinces = (
        db.query(func.count())
        .select_from(Province)
        .filter(Province.decision_number.isnot(None))
        .scalar()
        or 0
    )
    enriched_wards = (
        db.query(func.count())
        .select_from(Ward)
        .filter(Ward.decision_number.isnot(None))
        .scalar()
        or 0
    )
    return {
        "enriched_provinces": enriched_provinces,
        "enriched_wards": enriched_wards,
    }

# Note: CRUD routes merged into core admin endpoints.

# ── ADDRESS PARSER RESEARCH ENDPOINTS ──

@api_router.get("/parser/status", tags=["AI Address Parser"], summary="Trạng thái nạp model AI")
def get_parser_status():
    """Trả về trạng thái nạp model AI (idle/loading/ready/error) cùng danh sách model đã sẵn sàng."""
    with parser_runtime_lock:
        loaded = parser_loading_state.get("loadedModels", [])
        # prelabeler is always available (rule-based); 4 neural stacks tracked for progress
        available = list(loaded) + ["prelabeler"]
        current_model = parser_loading_state.get("currentModel")

        total_models = 4  # phobert, mgte, llm, address_ner
        progress = (len(loaded) / total_models * 100) if loaded else 0
        
        return {
            "status": parser_loading_state["status"],
            "startedAt": parser_loading_state.get("startedAt"),
            "finishedAt": parser_loading_state.get("finishedAt"),
            "loadedModels": loaded,
            "availableModels": list(set(available)),
            "currentModel": current_model,
            "progress": progress,
            "errors": parser_loading_state.get("errors", {}),
            "corpusSize": len(parser_runtime_bundle.get("corpus", [])) if parser_runtime_bundle else 0,
            "nerModelId": (parser_runtime_bundle or {}).get("address_ner_model_id"),
        }


@api_router.post("/parser/reload", tags=["AI Address Parser"], summary="Tải lại model AI")
def reload_parser_models(current_user: str = Depends(get_current_user)):
    """Xóa bundle cũ và kích hoạt tải lại tất cả model AI ở background."""
    global parser_runtime_bundle, parser_loading_state
    with parser_runtime_lock:
        if parser_loading_state.get("status") == "loading":
            return {"status": "loading", "message": "Model đang được nạp, vui lòng chờ..."}
        # Reset bundle so next request or background thread reloads
        parser_runtime_bundle = None
        parser_loading_state["status"] = "idle"

    _start_background_model_loading()
    return {"status": "accepted", "message": "Đã kích hoạt tải lại model AI ở background"}


@api_router.get("/parser/sample", tags=["AI Address Parser"], summary="Lấy mẫu địa chỉ nghiên cứu")
def get_parser_sample(db: Session = Depends(get_db)):
    """Lấy ngẫu nhiên một địa chỉ từ hàng đợi để thử nghiệm phân tích bằng các mô hình AI."""
    """Lấy một mẫu địa chỉ ngẫu nhiên từ queue để nghiên cứu."""
    sample = _get_random_parser_sample(db)
    if not sample:
        raise HTTPException(status_code=404, detail="No samples found in queue")
    return _serialize_parser_sample(sample)


@api_router.post("/parser/analyze", tags=["AI Address Parser"], summary="Phân tích & So sánh mô hình AI")
def analyze_parser_address(data: dict, model: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Sử dụng đồng thời các mô hình (PhoBERT, mGTE, Qwen) để phân tách và chuẩn hóa địa chỉ.
    Dùng để so sánh độ chính xác giữa các thuật toán AI khác nhau.
    """
    """
    Phân tích địa chỉ bằng nhiều mô hình (Research Comparison).
    Hỗ trợ cả phân tích từ ID (trong DB) hoặc text thô.
    Tham số 'model' cho phép chỉ định chạy 1 mô hình cụ thể (incremental updates).
    """
    sample_id = data.get("id")
    raw_text = data.get("raw_address")
    
    if sample_id:
        row = (
            db.query(*_queue_sample_columns())
            .filter(AddressCleansingQueue.id == sample_id)
            .first()
        )
        sample = _to_queue_sample(row)
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
        return _run_parser_research(sample, target_model=model)
    except Exception as e:
        logger.error(f"Parser Research Error: {str(e)}")
        # Fallback: Trả về kết quả tối thiểu để tránh 500
        try:
            from app.ai.export_for_annotation import PreLabeler
            prelabeler_result = PreLabeler.predict(
                sample.raw_address or raw_text,
                sample.ward_name,
                sample.district_name,
                sample.province_name
            )
            return {
                "sample": _serialize_parser_sample(sample) if sample_id else {"raw_address": raw_text},
                "analysis_input": sample.raw_address or raw_text,
                "outputs": {
                    "prelabeler": {
                        "mode": "rule_based_hybrid_fallback",
                        "result": prelabeler_result,
                        "entityCount": len(prelabeler_result),
                    }
                },
                "error": str(e),
                "meta": {
                    "corpusSize": 0,
                    "evaluatedAt": datetime.utcnow().isoformat() + "Z",
                    "note": "FALLBACK MODE: AI Models failed to load or crashed. Using Rule-based engine."
                }
            }
        except Exception as fallback_err:
            logger.error(f"Critical Fallback Error: {str(fallback_err)}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": f"Model error: {str(e)}. Fallback error: {str(fallback_err)}",
                    "note": "Service partially unavailable",
                }
            )

def _read_explorer_queue(
    db: Session,
    page: int,
    limit: int,
    q: str,
    province_id: Optional[int],
    district_id: Optional[int],
    ward_id: Optional[int],
):
    try:
        query = db.query(
            AddressCleansingQueue.id,
            AddressCleansingQueue.raw_address,
            AddressCleansingQueue.ward_name,
            AddressCleansingQueue.district_name,
            AddressCleansingQueue.province_name,
            AddressCleansingQueue.processing_status,
        )
        if ward_id is not None:
            query = query.filter(AddressCleansingQueue.ward_id == ward_id)
        elif district_id is not None:
            query = query.filter(AddressCleansingQueue.district_id == district_id)
        elif province_id is not None:
            query = query.filter(AddressCleansingQueue.province_id == province_id)

        q_stripped = (q or "").strip()
        if q_stripped:
            term = f"%{q_stripped}%"
            query = query.filter(
                or_(
                    AddressCleansingQueue.raw_address.ilike(term),
                    AddressCleansingQueue.ward_name.ilike(term),
                    AddressCleansingQueue.district_name.ilike(term),
                    AddressCleansingQueue.province_name.ilike(term),
                    AddressCleansingQueue.processing_status.ilike(term),
                )
            )

        total = query.count()
        offset = (page - 1) * limit
        samples = (
            query.order_by(AddressCleansingQueue.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": [
                {
                    "id": s.id,
                    "raw_address": s.raw_address,
                    "ward_name": s.ward_name,
                    "district_name": s.district_name,
                    "province_name": s.province_name,
                    "status": s.processing_status or "PENDING",
                }
                for s in samples
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }
    except Exception as e:
        logger.warning(f"Explorer queue fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi Tìm kiếm prq.address_cleansing_queue: {str(e)}")


@api_router.get("/explorer/queue", tags=["Xử lý hàng loạt"], summary="Danh sách hàng đợi chuẩn hóa")
def get_explorer_queue(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    province_id: Optional[int] = Query(None),
    district_id: Optional[int] = Query(None),
    ward_id: Optional[int] = Query(None),
):
    """Lấy danh sách các địa chỉ đang chờ hoặc đã xử lý trong hàng đợi chuẩn hóa."""
    return _read_explorer_queue(db, page, limit, q, province_id, district_id, ward_id)


@app.get("/explorer/queue")
def get_explorer_queue_root(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    province_id: Optional[int] = Query(None),
    district_id: Optional[int] = Query(None),
    ward_id: Optional[int] = Query(None),
):
    return _read_explorer_queue(db, page, limit, q, province_id, district_id, ward_id)

@api_router.get("/label-studio/debug", tags=["AI Address Parser"], summary="Kiểm tra kết nối Label Studio")
async def debug_ls_connection(current_user: str = Depends(get_current_user)):
    """Kiểm tra cấu hình và kết nối tới API của Label Studio."""
    ls_token = os.getenv("LABEL_STUDIO_API_TOKEN")
    ls_url = (os.getenv("LABEL_STUDIO_URL", "https://label.nod.io.vn") or "").strip()
    project_id = os.getenv("LABEL_STUDIO_PROJECT_ID", "1")

    if not ls_token:
        return {"status": "error", "message": "LABEL_STUDIO_API_TOKEN chưa được cấu hình trong .env"}

    results = []
    # Endpoint candidates: 
    # 1. /api/tasks/?project=X (Standard tasks list with filter)
    # 2. /api/projects/X/tasks (Project specific tasks)
    # 3. /api/projects/ (List projects to check auth)
    
    ls_url_clean = ls_url.rstrip('/')
    test_urls = [
        ("Auth Check", f"{ls_url_clean}/api/projects/"),
        ("Project Tasks", f"{ls_url_clean}/api/projects/{project_id}/tasks"),
        ("Standard Tasks", f"{ls_url_clean}/api/tasks/?project={project_id}")
    ]

    auth_headers = [
        ("Token", {"Authorization": f"Token {ls_token}"}),
        ("Bearer", {"Authorization": f"Bearer {ls_token}"})
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url_name, url in test_urls:
            for auth_name, headers in auth_headers:
                try:
                    logger.info(f"Label Studio Debug: Testing {url_name} with {auth_name} auth")
                    resp = await client.get(url, headers=headers)
                    results.append({
                        "test": url_name,
                        "auth": auth_name,
                        "status_code": resp.status_code,
                        "success": resp.status_code == 200,
                        "message": resp.text[:200] if resp.status_code != 200 else "Success"
                    })
                    if resp.status_code == 200:
                        # Found a working combination
                        return {
                            "status": "success",
                            "message": f"Kết nối thành công bằng {auth_name} tới {url_name}",
                            "working_config": {"auth": auth_name, "test": url_name},
                            "details": results
                        }
                except Exception as e:
                    results.append({
                        "test": url_name,
                        "auth": auth_name,
                        "status_code": 0,
                        "success": False,
                        "message": str(e)
                    })

    return {
        "status": "error", 
        "message": "Không thể kết nối tới Label Studio với các cấu hình hiện tại. Vui lòng kiểm tra lại Token và URL.",
        "details": results
    }

@api_router.post("/label-studio/sync", tags=["AI Address Parser"], summary="Đồng bộ dữ liệu đã gán nhãn về Training Hub")
async def sync_ls_to_training(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Tự động tải các task đã gán nhãn từ Label Studio và lưu vào CSDL huấn luyện."""
    ls_token = os.getenv("LABEL_STUDIO_API_TOKEN")
    ls_url = (os.getenv("LABEL_STUDIO_URL", "https://label.nod.io.vn") or "").strip()
    project_id = os.getenv("LABEL_STUDIO_PROJECT_ID", "1")

    if not ls_token:
        raise HTTPException(status_code=400, detail="Label Studio API Token chưa được cấu hình.")

    ls_api_url = f"{ls_url.rstrip('/')}/api/tasks/"
    params = {"project": project_id, "page_size": 1000}
    headers = {"Authorization": f"Token {ls_token}"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ls_api_url, headers=headers, params=params)
            if response.status_code != 200:
                # Try Bearer
                headers = {"Authorization": f"Bearer {ls_token}"}
                response = await client.get(ls_api_url, headers=headers, params=params)

            if response.status_code != 200:
                if response.status_code in (401, 403):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            "Label Studio từ chối xác thực — kiểm tra LABEL_STUDIO_API_TOKEN và quyền đọc project "
                            f"(upstream HTTP {response.status_code})."
                        ),
                    )
                raise HTTPException(
                    status_code=response.status_code, detail="Không thể tải dữ liệu từ Label Studio."
                )

            data = response.json()
            all_tasks = data if isinstance(data, list) else data.get("tasks", data.get("results", []))
            
            # Filter tasks with annotations
            labeled_tasks = [t for t in all_tasks if t.get("annotations") and len(t["annotations"]) > 0]
            
            count_new = 0
            count_skipped = 0
            
            for task in labeled_tasks:
                ls_id = task.get("id")
                # Check if already imported (using external_id if possible or just raw_text check)
                raw_text = task.get("data", {}).get("text", task.get("data", {}).get("address", ""))
                if not raw_text:
                    continue
                
                exists = db.query(TrainingDataset).filter(TrainingDataset.raw_text == raw_text).first()
                if exists:
                    count_skipped += 1
                    continue
                
                # Convert LS annotations to BIO tags
                # This is a simplified conversion for the project's labels
                annotation = task["annotations"][0] # Take the first annotation
                results = annotation.get("result", [])
                
                # Sort results by start position
                results.sort(key=lambda x: x.get("value", {}).get("start", 0))
                
                # For simplicity, we store the raw results as ner_tags_json 
                # because the training pipeline can handle them or we can convert them later.
                # However, the DB schema says BIO tags array.
                # Let's store a compatible format.
                
                new_entry = TrainingDataset(
                    raw_text=raw_text,
                    ner_tags_json=results,
                    is_synthetic=False,
                    noise_level="low"
                )
                db.add(new_entry)
                count_new += 1
            
            db.commit()
            
            return {
                "status": "success",
                "message": f"Đã đồng bộ {count_new} bản ghi mới từ Label Studio ({count_skipped} bản ghi đã tồn tại).",
                "total_labeled_found": len(labeled_tasks),
                "new_imported": count_new
            }
            
    except Exception as e:
        logger.error(f"Error syncing Label Studio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/label-studio/tasks", tags=["AI Address Parser"], summary="Lấy Task từ Label Studio")
async def get_ls_tasks(current_user: str = Depends(get_current_user)):
    """Truy xuất danh sách các tác vụ gán nhãn dữ liệu từ API của Label Studio."""
    ls_token = os.getenv("LABEL_STUDIO_API_TOKEN")
    ls_url = (os.getenv("LABEL_STUDIO_URL", "https://label.nod.io.vn") or "").strip()
    project_id = os.getenv("LABEL_STUDIO_PROJECT_ID", "1")

    if not ls_token:
        logger.warning("LABEL_STUDIO_API_TOKEN not found in environment. Returning mock data.")
        return [
            {"id": 101, "data": {"address": "2695/7 Phạm Thế Hiển, P7, Q8, HCM"}, "created_at": "2026-04-28T10:00:00Z", "is_labeled": True, "project": project_id},
            {"id": 102, "data": {"address": "123 Lê Lợi, Bến Thành, Q1, HCM"}, "created_at": "2026-04-28T11:00:00Z", "is_labeled": False, "project": project_id},
            {"id": 103, "data": {"address": "456 Nguyễn Huệ, Q1, HCM"}, "created_at": "2026-04-29T00:15:00Z", "is_labeled": False, "project": project_id},
        ]

    # Try standard tasks endpoint first
    ls_api_url = f"{ls_url.rstrip('/')}/api/tasks/"
    params = {"project": project_id, "page_size": 100}
    
    # Try multiple auth modes
    headers_token = {"Authorization": f"Token {ls_token}"}
    headers_bearer = {"Authorization": f"Bearer {ls_token}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Try Token auth (Standard)
            response = await client.get(ls_api_url, headers=headers_token, params=params)
            
            # 2. Try Bearer if Token failed or if it's a JWT
            if response.status_code != 200:
                logger.info(f"Label Studio Token auth failed (status={response.status_code}), trying Bearer...")
                response = await client.get(ls_api_url, headers=headers_bearer, params=params)

            # 3. Try fallback endpoint if still failed
            if response.status_code != 200:
                fallback_url = f"{ls_url.rstrip('/')}/api/projects/{project_id}/tasks"
                logger.info(f"Trying fallback Label Studio endpoint: {fallback_url}")
                response = await client.get(fallback_url, headers=headers_token)
                if response.status_code != 200:
                    response = await client.get(fallback_url, headers=headers_bearer)

            if response.status_code == 200:
                data = response.json()
                tasks = []
                if isinstance(data, list):
                    tasks = data
                elif isinstance(data, dict):
                    tasks = data.get("tasks", data.get("results", []))
                
                logger.info(f"Label Studio fetch success: project_id={project_id}, tasks_count={len(tasks)}")
                return tasks
            else:
                logger.error(f"Label Studio fetch failed after all attempts. Last status: {response.status_code}")
                if response.status_code in (401, 403):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            "Label Studio từ chối token hoặc quyền truy cập — cập nhật LABEL_STUDIO_API_TOKEN trong .env "
                            f"và đảm bảo token có quyền đọc project (upstream HTTP {response.status_code})."
                        ),
                    )
                raise HTTPException(
                    status_code=response.status_code if response.status_code >= 400 else 500,
                    detail=f"Label Studio API error: {response.status_code}",
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting to Label Studio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Register API router
api_router_v1 = APIRouter(prefix="/api/v1")
api_router_v1.include_router(api_router)

# ── Evidence manifest endpoints ──
def _get_evidence_dirs():
    project_root = Path(__file__).resolve().parents[2]
    return [project_root / "reports" / "evidence_real", project_root / "reports" / "evidence"]

def _find_latest_manifest(dirs: List[Path]) -> Optional[Path]:
    for d in dirs:
        try:
            if not d.exists():
                continue
            manifests = sorted(d.glob("evidence_manifest_*.json"), reverse=True)
            if manifests:
                return manifests[0]
        except Exception:
            continue
    return None

def _load_manifest(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@api_router.get("/evidence/manifest", tags=["Hệ thống"], summary="Lấy danh mục bằng chứng (Evidence)")
def evidence_manifest():
    """Trả về danh sách các tệp tin báo cáo, bằng chứng thực nghiệm mới nhất của hệ thống."""
    dirs = _get_evidence_dirs()
    manifest_path = _find_latest_manifest(dirs)
    if manifest_path is None:
        # Return empty manifest instead of 404 to avoid browser console noise
        return {"files": {}, "file_urls": {}, "generatedAt": None, "_empty": True}

    manifest = _load_manifest(manifest_path)
    files = manifest.get("files", {}) or {}
    # Build API file URLs (relative to /api/evidence/file)
    file_urls = {k: f"/api/evidence/file?key={k}" for k in files.keys()}
    manifest["file_urls"] = file_urls
    manifest["_manifest_path"] = str(manifest_path)
    return manifest


@api_router.get("/evidence/file", tags=["Hệ thống"], summary="Tải tệp tin bằng chứng")
def evidence_file(key: str):
    """Tải xuống một tệp tin cụ thể (báo cáo, JSON, ảnh) dựa trên khóa (key) từ manifest."""
    dirs = _get_evidence_dirs()
    manifest_path = _find_latest_manifest(dirs)
    if manifest_path is None:
        raise HTTPException(status_code=404, detail="No evidence manifest found")

    manifest = _load_manifest(manifest_path)
    files = manifest.get("files", {}) or {}
    if key not in files:
        raise HTTPException(status_code=404, detail=f"File key not found in manifest: {key}")

    manifest_dir = manifest_path.parent
    rel_path = Path(files[key])
    # Ensure we resolve inside the manifest directory
    file_path = (manifest_dir / rel_path).resolve()
    try:
        # Prevent serving files outside the manifest directory
        if not str(file_path).startswith(str(manifest_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access to requested file is forbidden")
    except Exception:
        raise HTTPException(status_code=403, detail="Access to requested file is forbidden")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested file does not exist")

    return FileResponse(str(file_path), filename=file_path.name)


# ── Cache Management Endpoints ──

@api_router.get("/cache/health", tags=["Cache"], summary="Trạng thái Redis cache")
def get_cache_health():
    """Trả về thông tin kết nối Redis và số lượng key cache đơn vị hành chính."""
    return cache_health()


@api_router.delete("/cache/admin", tags=["Cache"], summary="Xóa toàn bộ cache đơn vị hành chính")
def clear_admin_cache(level: Optional[str] = None):
    """
    Xóa cache đơn vị hành chính.
    - **level**: 'province', 'district', 'ward', 'mapping' hoặc để trống để xóa tất cả.
    """
    if level == "province":
        n = invalidate_provinces()
    elif level == "district":
        n = invalidate_districts()
    elif level == "ward":
        n = invalidate_wards()
    elif level == "mapping":
        n = invalidate_ward_mapping()
    elif level is None:
        n = invalidate_all_admin()
    else:
        raise HTTPException(status_code=400, detail="level phải là: province, district, ward, mapping hoặc để trống")
    return {"status": "cleared", "keys_deleted": n, "level": level or "all"}


# ── G1: SCD Type 2 History & Sync Log Endpoints ──────────────────────────────

@api_router.get("/admin-unit/{level}/{unit_id}/history")
def get_admin_unit_history(
    level: str,
    unit_id: int,
    at: Optional[str] = Query(None, description="ISO date YYYY-MM-DD — trả về trạng thái tại thời điểm đó"),
    db: Session = Depends(get_db),
):
    """
    Tìm kiếm lịch sử SCD Type 2 của một đơn vị hành chính.

    - GET /api/admin-unit/ward/770001/history        → Toàn bộ lịch sử
    - GET /api/admin-unit/ward/770001/history?at=2024-01-01 → Trạng thái tại ngày đó
    """
    if level not in ("province", "district", "ward"):
        raise HTTPException(status_code=400, detail="level phải là: province, district, ward")

    at_dt = None
    if at:
        try:
            at_dt = datetime.strptime(at, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="at phải có định dạng YYYY-MM-DD")

    result = get_unit_at_date(db, level, unit_id, at_dt)

    if at_dt:
        if not result:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy {level} {unit_id} tại {at}")
        return {
            "unit_id": unit_id,
            "level": level,
            "at": at,
            "record": {c.name: getattr(result, c.name) for c in result.__table__.columns},
        }
    else:
        if not result:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy {level} với id={unit_id}")
        return {
            "unit_id": unit_id,
            "level": level,
            "total_versions": len(result),
            "history": [
                {c.name: getattr(r, c.name) for c in r.__table__.columns}
                for r in result
            ],
        }


@api_router.get("/sync-logs")
def get_sync_logs(
    run_id: Optional[str] = Query(None, description="UUID của lần chạy đồng bộ"),
    level: Optional[str] = Query(None, description="province | district | ward"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Lấy danh sách sync log. Có thể lọc theo run_id hoặc level."""
    q = db.query(SyncLog)
    if run_id:
        q = q.filter(SyncLog.run_id == run_id)
    if level:
        q = q.filter(SyncLog.level == level)
    logs = q.order_by(SyncLog.synced_at.desc()).limit(limit).all()
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "sync_source": log.sync_source,
                "level": log.level,
                "unit_id": log.unit_id,
                "change_type": log.change_type,
                "synced_at": log.synced_at.isoformat() if log.synced_at else None,
                "run_id": log.run_id,
                "records_affected": log.records_affected,
            }
            for log in logs
        ],
    }


@api_router.get("/sync-logs/summary/{run_id}")
def get_sync_log_summary(run_id: str, db: Session = Depends(get_db)):
    """Tổng hợp kết quả một lần chạy đồng bộ theo run_id."""
    summary = get_sync_summary(db, run_id)
    return summary


# ── G5: Temporal Address Migration ────────────────────────────────────────────

class MigrateAddressRequest(BaseModel):
    address: str
    province_id: Optional[int] = None


@api_router.post(
    "/migrate-address",
    tags=["AI Address Parser"],
    summary="Chuyển đổi địa chỉ Pre-2025 → Post-2025",
)
def migrate_address(payload: MigrateAddressRequest, db: Session = Depends(get_db)):
    """
    Phát hiện địa chỉ Pre-2025 và chuyển đổi sang tên đơn vị hành chính Post-2025.

    - Phát hiện epoch (PRE_2025 / POST_2025 / AMBIGUOUS)
    - Áp dụng WardMapping để thay tên cũ → tên mới
    - Trả về địa chỉ đã chuyển đổi kèm metadata
    """
    from app.ai.epoch_detector import EpochDetector
    from app.ai.acs_calculator import ACSCalculator

    detector = EpochDetector(db_session=db)
    epoch_result = detector.detect(payload.address)

    conversion_result = {"converted_address": payload.address, "mapping_applied": False}
    if epoch_result.epoch == "PRE_2025":
        conversion_result = detector.convert_pre_to_post(
            payload.address, province_id=payload.province_id
        )

    acs_calc = ACSCalculator(db_session=db)
    acs_comp = acs_calc.compute(
        raw_address=payload.address,
        standardized_address=conversion_result.get("converted_address", payload.address),
        semantic_score=conversion_result.get("confidence", 0.5),
        admin_version=2 if epoch_result.epoch != "PRE_2025" else 1,
    )

    return {
        "original_address":   payload.address,
        "epoch":              epoch_result.epoch,
        "epoch_confidence":   epoch_result.confidence,
        "converted_address":  conversion_result.get("converted_address"),
        "mapping_applied":    conversion_result.get("mapping_applied", False),
        "mappings_used":      conversion_result.get("mappings_used", []),
        "acs_score":          acs_comp.acs_score,
        "acs_decision":       acs_comp.acs_decision,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  PreLabeler Labeling Suite API
#  Table: ai.prelabeler_testcases (created via migration below)
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_prelabeler_testcases_table():
    """Create ai.prelabeler_testcases table if it doesn't exist."""
    ddl = text("""
        CREATE SCHEMA IF NOT EXISTS ai;
        CREATE TABLE IF NOT EXISTS ai.prelabeler_testcases (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL DEFAULT '',
            input       JSONB NOT NULL DEFAULT '{}',
            note        TEXT NOT NULL DEFAULT '',
            expected    JSONB NOT NULL DEFAULT '[]',
            strict      BOOLEAN NOT NULL DEFAULT FALSE,
            test_result JSONB NULL,
            tested_at   TIMESTAMPTZ NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        ALTER TABLE ai.prelabeler_testcases ADD COLUMN IF NOT EXISTS note TEXT NOT NULL DEFAULT '';
        ALTER TABLE ai.prelabeler_testcases ADD COLUMN IF NOT EXISTS test_result JSONB NULL;
        ALTER TABLE ai.prelabeler_testcases ADD COLUMN IF NOT EXISTS tested_at TIMESTAMPTZ NULL;
    """)
    try:
        with engine.connect() as conn:
            conn.execute(ddl)
            # Data migration:
            # - input: JSON object -> raw_address string
            # - expected: merge old expected + admin labels from input object
            rows = conn.execute(text(
                "SELECT id, input, note, expected FROM ai.prelabeler_testcases"
            )).mappings().all()
            for r in rows:
                inp = r.get("input")
                exp = r.get("expected") or []
                if isinstance(exp, str):
                    try:
                        exp = json.loads(exp)
                    except Exception:
                        exp = []
                if not isinstance(exp, list):
                    exp = []

                raw_address = ""
                admin_items = []
                if isinstance(inp, dict):
                    raw_address = str(inp.get("raw_address") or "").strip()
                    ward = str(inp.get("ward_name") or "").strip()
                    district = str(inp.get("district_name") or "").strip()
                    province = str(inp.get("province_name") or "").strip()
                    if ward:
                        admin_items.append({"label": "WDS", "text": ward})
                    if district:
                        admin_items.append({"label": "DST", "text": district})
                    if province:
                        admin_items.append({"label": "PRO", "text": province})
                elif isinstance(inp, str):
                    raw_address = inp.strip()
                else:
                    raw_address = str(inp or "").strip()

                merged_expected = []
                seen = set()
                for item in [*admin_items, *exp]:
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label") or "").strip().upper()
                    text_val = str(item.get("text") or "").strip()
                    if not label or not text_val:
                        continue
                    key = (label, text_val.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    merged_expected.append({"label": label, "text": text_val})

                conn.execute(text("""
                    UPDATE ai.prelabeler_testcases
                    SET input = CAST(:input AS JSONB),
                        note = :note,
                        expected = CAST(:expected AS JSONB),
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": r["id"],
                    "input": json.dumps(raw_address, ensure_ascii=False),
                    "note": str(r.get("note") or "").strip(),
                    "expected": json.dumps(merged_expected, ensure_ascii=False),
                })
            conn.commit()
        logger.info("ai.prelabeler_testcases table ensured")
    except Exception as e:
        logger.warning(f"Failed to create prelabeler_testcases table: {e}")

# Run migration at import time (idempotent)
_ensure_prelabeler_testcases_table()


class PreLabelerLabelingCase(BaseModel):
    # input moi: raw_address string; expected gom ca admin labels + user labels.
    id: Optional[Any] = None
    name: Optional[Any] = ""
    input: Optional[Any] = None
    note: Optional[Any] = ""
    expected: Optional[List[Dict[str, Any]]] = None
    strict: Optional[Any] = False


class PreLabelerLabelingRunPayload(BaseModel):
    cases: List[PreLabelerLabelingCase]


class PreLabelerExportPayload(BaseModel):
    limit: int = 500
    config_path: Optional[str] = "app/ai/config.yaml"


@api_router.get("/prelabeler-cases", tags=["PreLabeler Labeling Suite"])
def list_prelabeler_cases(current_user=Depends(get_current_user)):
    """Lay tat ca labeling cases tu database."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, name, input, note, expected, strict, test_result, tested_at, created_at, updated_at "
                "FROM ai.prelabeler_testcases ORDER BY created_at ASC"
            )).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")


@api_router.get("/prelabeler-cases/random-predict", tags=["PreLabeler Labeling Suite"])
def random_prelabeler_predict(current_user=Depends(get_current_user)):
    """
    Lay ngau nhien 1 raw_address trong queue chua ton tai o bo cases,
    sau đó chạy PreLabeler.predict và trả về expected gợi ý.
    """
    from app.ai.export_for_annotation import PreLabeler

    fast_random_sql = text("""
        WITH used AS (
            SELECT DISTINCT
                t.input_raw_address_norm AS raw_norm
            FROM ai.prelabeler_testcases t
            WHERE t.input_raw_address_norm IS NOT NULL
        )
        SELECT
            q.id,
            q.raw_address,
            q.ward_name,
            q.district_name,
            q.province_name
        FROM prq.address_cleansing_queue q TABLESAMPLE SYSTEM (:sample_pct)
        LEFT JOIN used u
            ON q.raw_address_norm = u.raw_norm
        WHERE q.raw_address_norm IS NOT NULL
          AND u.raw_norm IS NULL
        ORDER BY RANDOM()
        LIMIT 1
    """)

    fallback_sql = text("""
        WITH used AS (
            SELECT DISTINCT
                t.input_raw_address_norm AS raw_norm
            FROM ai.prelabeler_testcases t
            WHERE t.input_raw_address_norm IS NOT NULL
        )
        SELECT
            q.id,
            q.raw_address,
            q.ward_name,
            q.district_name,
            q.province_name
        FROM prq.address_cleansing_queue q
        LEFT JOIN used u
            ON q.raw_address_norm = u.raw_norm
        WHERE q.raw_address_norm IS NOT NULL
          AND u.raw_norm IS NULL
        ORDER BY RANDOM()
        LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            row = None
            # Ưu tiên chiến lược nhanh: quét mẫu ngẫu nhiên nhỏ trước, tăng dần nếu chưa trúng.
            for pct in (0.1, 0.3, 0.7, 1.5, 3.0):
                row = conn.execute(
                    fast_random_sql,
                    {"sample_pct": pct},
                ).mappings().first()
                if row:
                    break

            # Fallback để giữ behavior đúng ngay cả khi sample quá nhỏ.
            if not row:
                row = conn.execute(fallback_sql).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Khong con du lieu ngau nhien chua co trong cases")

        raw_address = str(row.get("raw_address") or "").strip()
        ward_name = str(row.get("ward_name") or "").strip() or None
        district_name = str(row.get("district_name") or "").strip() or None
        province_name = str(row.get("province_name") or "").strip() or None

        predictions = PreLabeler.predict(
            raw_address=raw_address,
            ward_name=ward_name,
            district_name=district_name,
            province_name=province_name,
        )
        expected = predictions_to_expected(predictions)
        expected = enforce_admin_type_name(
            expected=expected,
            raw_address=raw_address,
            ward_name=ward_name,
            district_name=district_name,
            province_name=province_name,
        )

        return {
            "source_id": row.get("id"),
            "raw_address": raw_address,
            "expected": expected,
            "meta": {
                "ward_name": ward_name,
                "district_name": district_name,
                "province_name": province_name,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Random predict failed: {e}")


@api_router.post("/prelabeler-cases", tags=["PreLabeler Labeling Suite"])
def save_prelabeler_cases(cases: List[PreLabelerLabelingCase], current_user=Depends(get_current_user)):
    """Upsert toan bo danh sach labeling cases (replace all strategy)."""
    try:
        with engine.begin() as conn:
            ids = [str(c.id or f"case_{i}") for i, c in enumerate(cases)]
            if ids:
                # Manual placeholders to avoid SQLAlchemy IN clause mapping issues with text()
                placeholders = ", ".join([f":id_{i}" for i in range(len(ids))])
                params = {f"id_{i}": val for i, val in enumerate(ids)}
                conn.execute(text(f"DELETE FROM ai.prelabeler_testcases WHERE id NOT IN ({placeholders})"), params)
            else:
                conn.execute(text("DELETE FROM ai.prelabeler_testcases"))
            
            # Upsert each case
            for i, c in enumerate(cases):
                case_id = str(c.id or f"case_{i}")
                raw_input = c.input if isinstance(c.input, str) else ""
                admin_from_input = []
                if isinstance(c.input, dict):
                    raw_input = str(c.input.get("raw_address") or "")
                    ward = str(c.input.get("ward_name") or "").strip()
                    district = str(c.input.get("district_name") or "").strip()
                    province = str(c.input.get("province_name") or "").strip()
                    if ward:
                        admin_from_input.append({"label": "WDS", "text": ward})
                    if district:
                        admin_from_input.append({"label": "DST", "text": district})
                    if province:
                        admin_from_input.append({"label": "PRO", "text": province})

                expected_items = c.expected or []
                normalized_expected = []
                seen = set()
                for item in [*admin_from_input, *expected_items]:
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label") or "").strip().upper()
                    text_val = str(item.get("text") or "").strip()
                    if not label or not text_val:
                        continue
                    k = (label, text_val.lower())
                    if k in seen:
                        continue
                    seen.add(k)
                    normalized_expected.append({"label": label, "text": text_val})

                conn.execute(text("""
                    INSERT INTO ai.prelabeler_testcases (id, name, input, note, expected, strict, test_result, tested_at, updated_at)
                    VALUES (:id, :name, CAST(:input AS JSONB), :note, CAST(:expected AS JSONB), :strict, NULL, NULL, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        input = EXCLUDED.input,
                        note = EXCLUDED.note,
                        expected = EXCLUDED.expected,
                        strict = EXCLUDED.strict,
                        test_result = NULL,
                        tested_at = NULL,
                        updated_at = NOW()
                """), {
                    "id": case_id,
                    "name": c.name or "",
                    "input": json.dumps(str(raw_input or "").strip(), ensure_ascii=False),
                    "note": str(c.note or "").strip(),
                    "expected": json.dumps(normalized_expected, ensure_ascii=False),
                    "strict": bool(c.strict),
                })
        return {"ok": True, "count": len(cases)}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Save PreLabeler tests failed: {e}\n{tb}")
        raise HTTPException(500, f"DB error: {str(e)}")


@api_router.delete("/prelabeler-cases/{case_id}", tags=["PreLabeler Labeling Suite"])
def delete_prelabeler_case(case_id: str, current_user=Depends(get_current_user)):
    """Xoa mot labeling case theo ID."""
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM ai.prelabeler_testcases WHERE id = :id"), {"id": case_id})
            conn.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")


@api_router.post("/prelabeler-cases/run", tags=["PreLabeler Labeling Suite"])
def run_prelabeler_cases(payload: PreLabelerLabelingRunPayload, current_user=Depends(get_current_user)):
    """Chay PreLabeler.predict() cho tung labeling case va so sanh voi expected."""
    from app.ai.export_for_annotation import PreLabeler

    results = []
    for idx, case in enumerate(payload.cases):
        expected = case.expected or []  # [{"label": "STR", "text": "Tam Bình"}]
        case_id = str(case.id or f"case_{idx}")
        raw_address = case.input if isinstance(case.input, str) else ""
        if isinstance(case.input, dict):
            raw_address = str(case.input.get("raw_address") or "")
        raw_address = str(raw_address or "").strip()
        ward_name = first_expected_text(expected, "WDS")
        district_name = first_expected_text(expected, "DST")
        province_name = first_expected_text(expected, "PRO")

        try:
            predictions = PreLabeler.predict(
                raw_address=raw_address,
                ward_name=ward_name,
                district_name=district_name,
                province_name=province_name,
            )
        except Exception as e:
            results.append({
                "id": case_id, "passed": False, "error": str(e),
                "actual": [], "expected": expected, "details": [], "unexpected": []
            })
            continue

        actual = [
            {"label": p["value"]["labels"][0], "text": p["value"]["text"]}
            for p in predictions
        ]

        validation = validate_expected_against_actual(
            raw_address=raw_address,
            expected=expected,
            actual=actual,
        )

        results.append({
            "id": case_id, "passed": bool(validation.get("passed")),
            "actual": actual, "expected": expected,
            "details": validation.get("details", []),
            "unexpected": validation.get("unexpected", []),
            "validation_errors": validation.get("validation_errors", []),
        })

    # Persist latest run result and time.
    try:
        with engine.begin() as conn:
            for r in results:
                conn.execute(text("""
                    UPDATE ai.prelabeler_testcases
                    SET test_result = CAST(:test_result AS JSONB),
                        tested_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": r.get("id"),
                    "test_result": json.dumps(r, ensure_ascii=False),
                })
    except Exception as e:
        logger.warning(f"Failed to persist prelabeler run results: {e}")

    return results


@api_router.post("/prelabeler-cases/export-label-studio", tags=["PreLabeler Labeling Suite"])
def export_prelabeler_label_studio(payload: PreLabelerExportPayload, current_user=Depends(get_current_user)):
    """Export dữ liệu prelabel sang JSON/XML cho Label Studio, tương tự script CLI."""
    from app.ai.export_for_annotation import export_data

    limit = int(payload.limit or 0)
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit phải > 0")

    config_path = str(payload.config_path or "app/ai/config.yaml").strip()
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"ner_samples_{date_str}_{limit}"
    zip_name = f"{base_name}_label_studio.zip"

    try:
        with tempfile.TemporaryDirectory(prefix="vnai_prelabeler_export_") as tmpdir:
            output_file = Path(tmpdir) / f"{base_name}_prelabeled.json"
            export_data(config_path, str(output_file), limit)
            config_file = Path(str(output_file.with_suffix(".xml")).replace("_prelabeled", "_config"))

            if not output_file.exists() or not config_file.exists():
                raise RuntimeError("Export xong nhưng không tìm thấy file JSON/XML")

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(output_file, arcname=output_file.name)
                zf.write(config_file, arcname=config_file.name)
            buffer.seek(0)
    except Exception as e:
        logger.error(f"Export prelabeler data failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    headers = {"Content-Disposition": f'attachment; filename="{zip_name}"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@api_router.get("/prelabeler-cases/export-file", tags=["PreLabeler Labeling Suite"])
def download_prelabeler_export_file(name: str, current_user=Depends(get_current_user)):
    """Tải file đã export từ thư mục data."""
    safe_name = Path(str(name or "")).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Thiếu tên file")
    if not (safe_name.endswith(".json") or safe_name.endswith(".xml")):
        raise HTTPException(status_code=400, detail="Chỉ cho phép tải .json hoặc .xml")
    if not safe_name.startswith("ner_samples_"):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ")

    file_path = (Path("data") / safe_name).resolve()
    data_dir = Path("data").resolve()
    if not str(file_path).startswith(str(data_dir)):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file")
    return FileResponse(str(file_path), filename=file_path.name)


api_router.include_router(boundary_router, prefix="/boundary")
api_router.include_router(spatial_router)
app.include_router(api_router, prefix="/api") # Match frontend API_BASE
app.include_router(api_router_v1) # Support /api/v1/*

if __name__ == "__main__":
    import uvicorn
    # Changed port to 8081 to match VPS setup (avoiding 8080 which might be used by Docker)
    uvicorn.run(app, host="0.0.0.0", port=8081)
