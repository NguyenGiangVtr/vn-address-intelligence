import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

import sys
import os
sys.path.append(os.getcwd())
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    res = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'mat' AND table_name = 'ward_mapping'")).fetchall()
    print([r[0] for r in res])
finally:
    db.close()
