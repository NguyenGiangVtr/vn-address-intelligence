import os
from dotenv import load_dotenv
from pathlib import Path
import urllib.parse

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    DB_HOST = os.getenv("DB_HOST", "157.66.81.69")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "vnai_admin")
    DB_PASS = os.getenv("DB_PASS", "vnai_admin@97GHxafU")
    DB_NAME = os.getenv("DB_NAME", "vn_address_intelligence_db")
    
    # Encode password to handle special characters like '@'
    encoded_pass = urllib.parse.quote_plus(DB_PASS)
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Schemas
    SCHEMAS = ["mat", "osm", "ath", "prq"]

    # OSM Settings
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
