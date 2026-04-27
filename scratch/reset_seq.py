from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Resetting sequences...")
    conn.execute(text("SELECT setval('mat.province_province_id_seq', (SELECT COALESCE(max(province_id), 0) + 1 FROM mat.province))"))
    conn.execute(text("SELECT setval('mat.district_district_id_seq', (SELECT COALESCE(max(district_id), 0) + 1 FROM mat.district))"))
    conn.execute(text("SELECT setval('mat.ward_ward_id_seq', (SELECT COALESCE(max(ward_id), 0) + 1 FROM mat.ward))"))
    conn.commit()
    print("Done.")
