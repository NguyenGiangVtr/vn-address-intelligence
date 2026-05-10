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
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Adding district_id_new column...")
    conn.execute(text("ALTER TABLE mat.ward_mapping ADD COLUMN IF NOT EXISTS district_id_new INTEGER"))
    conn.commit()
    print("Done.")
