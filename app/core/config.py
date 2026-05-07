from __future__ import annotations
import os
from dotenv import load_dotenv
from pathlib import Path
import urllib.parse

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def _typesense_export_read_timeout():
    raw = os.getenv("TYPESENSE_EXPORT_READ_TIMEOUT_SEC", "").strip()
    if raw in ("", "0", "none", "None"):
        return None
    return float(raw)


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

    # SMTP Settings
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
