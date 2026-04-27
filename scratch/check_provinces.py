
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
