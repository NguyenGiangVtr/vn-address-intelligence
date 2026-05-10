import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()


import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.nso_api import get_nso_provinces
from datetime import datetime

def check_provinces():
    print("Fetching Provinces...")
    provinces = get_nso_provinces()
    for p in provinces[:5]:
        print(f"- {p.get('MaTinh')}: {p.get('TenTinh')}")

if __name__ == "__main__":
    check_provinces()
