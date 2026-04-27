
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.nso_api import get_nso_provinces, get_nso_districts, get_nso_wards
from datetime import datetime

def test_nso_data():
    print("Fetching Provinces...")
    provinces = get_nso_provinces()
    if provinces:
        print(f"Sample Province: {provinces[0]}")
        p_code = provinces[0].get("MaTinh")
        p_name = provinces[0].get("TenTinh")
        
        print(f"\nFetching Districts for {p_name} ({p_code})...")
        districts = get_nso_districts(p_code, p_name)
        if districts:
            print(f"Sample District: {districts[0]}")
            d_code = districts[0].get("MaQuanHuyen")
            d_name = districts[0].get("TenQuanHuyen")
            
            print(f"\nFetching Wards for {d_name} ({d_code})...")
            wards = get_nso_wards(p_code, p_name, d_code, d_name)
            if wards:
                print(f"Sample Ward: {wards[0]}")
            else:
                print("No wards found.")
        else:
            print("No districts found.")
    else:
        print("No provinces found.")

if __name__ == "__main__":
    test_nso_data()
