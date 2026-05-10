import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

import os
import sys
sys.path.append(os.getcwd())
from app.core.database import SessionLocal
from app.services.nso_sync import sync_full_nso
import json

db = SessionLocal()
try:
    result = sync_full_nso(db)
    with open("sync_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Saved to sync_result.json")
except Exception as e:
    with open("sync_error.txt", "w", encoding="utf-8") as f:
        f.write(str(e))
    print("Exception saved to sync_error.txt")
finally:
    db.close()
