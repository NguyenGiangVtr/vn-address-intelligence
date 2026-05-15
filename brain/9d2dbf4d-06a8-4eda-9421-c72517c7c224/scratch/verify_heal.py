from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("--- Verifying Specific Healed Names ---")
    
    # Check Ba Đình
    res = conn.execute(text("SELECT district_name, type_name FROM mat.district WHERE district_name = 'Ba Đình' AND admin_version = 1")).fetchone()
    print(f"District Ba Đình: {res}")
    
    # Check Ngọc Hà
    res = conn.execute(text("SELECT ward_name, type_name FROM mat.ward WHERE ward_name = 'Ngọc Hà' AND admin_version = 1")).fetchone()
    print(f"Ward Ngọc Hà: {res}")
    
    # Check Hà Nội
    res = conn.execute(text("SELECT province_name, type_name FROM mat.province WHERE province_name = 'Hà Nội' AND admin_version = 1")).fetchone()
    print(f"Province Hà Nội: {res}")
    
    # Check for any remaining '?'
    count = conn.execute(text("SELECT COUNT(*) FROM mat.ward WHERE (ward_name LIKE '%?%' OR type_name LIKE '%?%')")).scalar()
    print(f"Remaining wards with '?': {count}")
