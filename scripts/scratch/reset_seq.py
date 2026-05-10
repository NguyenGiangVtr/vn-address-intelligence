import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Resetting sequences...")
    conn.execute(text("SELECT setval('mat.province_province_id_seq', (SELECT COALESCE(max(province_id), 0) + 1 FROM mat.province))"))
    conn.execute(text("SELECT setval('mat.district_district_id_seq', (SELECT COALESCE(max(district_id), 0) + 1 FROM mat.district))"))
    conn.execute(text("SELECT setval('mat.ward_ward_id_seq', (SELECT COALESCE(max(ward_id), 0) + 1 FROM mat.ward))"))
    conn.commit()
    print("Done.")
