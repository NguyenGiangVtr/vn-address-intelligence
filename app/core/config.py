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
    
    # Schemas
    SCHEMAS = ["mat", "osm", "ath", "prq"]

    # OSM Settings
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
