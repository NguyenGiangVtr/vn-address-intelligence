import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASS")
dbname = os.getenv("DB_NAME")

print(f"Connecting to {host}:{port} as {user} to {dbname}...")
try:
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
