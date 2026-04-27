import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.database import engine
from sqlalchemy import text

queries = {
    "Province NaN province_no": "SELECT COUNT(*) FROM mat.province WHERE province_no = 'nan' OR province_no IS NULL",
    "Province NULL province_name": "SELECT COUNT(*) FROM mat.province WHERE province_name IS NULL",
    "Province NULL type_name": "SELECT COUNT(*) FROM mat.province WHERE type_name IS NULL",
    "District NaN district_no": "SELECT COUNT(*) FROM mat.district WHERE district_no = 'nan' OR district_no IS NULL",
    "District NULL district_name": "SELECT COUNT(*) FROM mat.district WHERE district_name IS NULL",
    "Ward NaN ward_no": "SELECT COUNT(*) FROM mat.ward WHERE ward_no = 'nan' OR ward_no IS NULL",
    "Ward NULL ward_name": "SELECT COUNT(*) FROM mat.ward WHERE ward_name IS NULL",
    "Enriched prov (decision)": "SELECT COUNT(*) FROM mat.province WHERE decision_number IS NOT NULL",
    "Enriched ward (decision)": "SELECT COUNT(*) FROM mat.ward WHERE decision_number IS NOT NULL",
}

with engine.connect() as conn:
    for name, q in queries.items():
        val = conn.execute(text(q)).scalar()
        print(f"{name:45}: {val}")
    
    rows = conn.execute(text("SELECT province_id, province_name, province_no, admin_version FROM mat.province WHERE admin_version=2 LIMIT 3")).fetchall()
    print("\nSample v2 provinces:")
    for r in rows: print(f"  {r}")
