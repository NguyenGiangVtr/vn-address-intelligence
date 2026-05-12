from __future__ import annotations
import os
from dotenv import load_dotenv
from pathlib import Path
import urllib.parse

from app.paths import repo_root

# Load .env file (repository root; works with flat app/ or src/app/)
env_path = repo_root() / ".env"
load_dotenv(dotenv_path=env_path)

def _typesense_export_read_timeout():
    raw = os.getenv("TYPESENSE_EXPORT_READ_TIMEOUT_SEC", "").strip()
    if raw in ("", "0", "none", "None"):
        return None
    return float(raw)


def _parser_corpus_max_addresses() -> int:
    """Giới hạn số địa chỉ corpus khi load parser (Siamese / encoding). Mặc định 100000."""
    raw = os.getenv("PARSER_CORPUS_MAX_ADDRESSES", "").strip()
    if not raw:
        return 100_000
    try:
        n = int(raw)
        return max(1, min(n, 2_000_000))
    except ValueError:
        return 100_000


def _parser_mgte_device() -> str:
    """
    Thiết bị load mGTE (SentenceTransformer): auto | cpu | cuda.
    Trên một số VPS (CUDA/driver hoặc wheel lệch), load có thể lỗi embedding index;
    đặt PARSER_MGTE_DEVICE=cpu để thử.
    """
    raw = (os.getenv("PARSER_MGTE_DEVICE") or "auto").strip().lower()
    if raw in ("auto", "cpu", "cuda"):
        return raw
    return "auto"


def _jwt_access_token_expire_minutes() -> int:
    """Thời hạn JWT (phút). Mặc định 7 ngày; có thể giảm/tăng qua JWT_ACCESS_TOKEN_EXPIRE_MINUTES."""
    raw = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "").strip()
    if not raw:
        return 60 * 24 * 7  # 10080 phút
    try:
        n = int(raw)
        return max(5, min(n, 525600))  # tối thiểu 5 phút, tối đa 1 năm
    except ValueError:
        return 60 * 24 * 7


class Config:
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")
    
    # Encode password to handle special characters like '@'
    encoded_pass = urllib.parse.quote_plus(DB_PASS or "")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Old DB
    OLD_DB_HOST = os.getenv("OLD_DB_HOST")
    OLD_DB_PORT = os.getenv("OLD_DB_PORT", "5432")
    OLD_DB_USER = os.getenv("OLD_DB_USER")
    OLD_DB_PASS = os.getenv("OLD_DB_PASS")
    OLD_DB_NAME = os.getenv("OLD_DB_NAME")
    old_encoded_pass = urllib.parse.quote_plus(OLD_DB_PASS or "")
    OLD_SQLALCHEMY_DATABASE_URL = f"postgresql://{OLD_DB_USER}:{old_encoded_pass}@{OLD_DB_HOST}:{OLD_DB_PORT}/{OLD_DB_NAME}" if OLD_DB_HOST else None
    
    # Schemas
    SCHEMAS = ["mat", "osm", "ath", "prq"]

    # OSM Settings
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    # Kibana / Logstash
    KIBANA_LOG_ENABLED = os.getenv("KIBANA_LOG_ENABLED", "false").lower() == "true"
    KIBANA_LOG_HOST = os.getenv("KIBANA_LOG_HOST", "localhost")
    KIBANA_LOG_PORT = int(os.getenv("KIBANA_LOG_PORT", "5044"))
    KIBANA_LOG_APP_NAME = os.getenv("KIBANA_LOG_APP_NAME", "vn-address-intelligence")

    # Typesense
    TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
    TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
    TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
    TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "xyz")
    TYPESENSE_COLLECTION = os.getenv("TYPESENSE_COLLECTION", "google_addresses")
    # Crawl qua /documents/export (JSONL): batch_size Typesense streaming; timeout đọc 0/unset = không giới hạn
    TYPESENSE_EXPORT_REMOTE_BATCH_SIZE = int(os.getenv("TYPESENSE_EXPORT_REMOTE_BATCH_SIZE", "250"))
    TYPESENSE_EXPORT_CONNECT_TIMEOUT_SEC = int(os.getenv("TYPESENSE_EXPORT_CONNECT_TIMEOUT_SEC", "60"))
    TYPESENSE_EXPORT_READ_TIMEOUT_SEC = _typesense_export_read_timeout()
    TYPESENSE_EXPORT_PROGRESS_LINES = int(os.getenv("TYPESENSE_EXPORT_PROGRESS_LINES", "50000"))

    # Redis Cache
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    # JWT (đăng nhập API / UI)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = _jwt_access_token_expire_minutes()

    # Parser / Siamese: số địa chỉ tối đa load từ DB khi encode corpus
    PARSER_CORPUS_MAX_ADDRESSES = _parser_corpus_max_addresses()
    PARSER_MGTE_DEVICE = _parser_mgte_device()

    # SMTP Settings
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
