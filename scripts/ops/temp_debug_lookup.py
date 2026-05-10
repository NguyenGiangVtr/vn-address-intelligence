import sys
from pathlib import Path
_ops_dir = Path(__file__).resolve().parent
if str(_ops_dir) not in sys.path:
    sys.path.insert(0, str(_ops_dir))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

import sys
import os
sys.path.append(r'D:\2.GIT SOURCE\vn-address-intelligence')
from app.core.database import SessionLocal
from app.api.server import lookup_mapping

db = SessionLocal()
try:
    res = lookup_mapping(query=None, province_id=None, district_id=79, ward_id=None, version=2, db=db)
    print('RESULT', res)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
