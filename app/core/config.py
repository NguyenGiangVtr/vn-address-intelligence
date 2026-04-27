import os
from dotenv import load_dotenv
from pathlib import Path
import urllib.parse

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

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
