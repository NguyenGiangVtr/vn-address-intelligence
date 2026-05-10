import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

from app.core.database import engine, text
try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'ward_mapping'"))
        cols = [r[0] for r in res.fetchall()]
        print("Columns in ward_mapping:", cols)
except Exception as e:
    print("Error:", e)
