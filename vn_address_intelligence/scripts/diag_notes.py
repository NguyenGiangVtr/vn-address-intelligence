"""
Diagnostic: Kiem tra gia tri notes va province_no/ward_no hien tai
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from src.database import engine
from sqlalchemy import text

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

with engine.connect() as conn:
    print("=== PROVINCE v2 - notes sample ===")
    rows = conn.execute(text("""
        SELECT province_id, province_name, admin_version, province_no, 
               decision_number, notes
        FROM mat.province WHERE admin_version = 2 LIMIT 5
    """)).fetchall()
    for r in rows:
        print(f"  id={r[0]}, name={r[1]}, v={r[2]}, pno={r[3]}, dec={r[4]}")
        print(f"  notes={repr(r[5])}")
        print()

    print("=== WARD v2 - notes sample ===")
    rows = conn.execute(text("""
        SELECT ward_id, ward_name, admin_version, ward_no,
               decision_number, notes
        FROM mat.ward WHERE decision_number IS NOT NULL LIMIT 3
    """)).fetchall()
    for r in rows:
        print(f"  id={r[0]}, name={r[1]}, wno={r[3]}, dec={r[4]}")
        print(f"  notes={repr(r[5])}")
        print()

    print("=== PROVINCE v1 province_no ===")
    rows = conn.execute(text("SELECT province_id, province_name, province_no FROM mat.province WHERE admin_version=1 LIMIT 5")).fetchall()
    for r in rows: print(f"  id={r[0]}, name={r[1]}, no={r[2]}")

    print("\n=== PROVINCE v2 province_no ===")
    rows = conn.execute(text("SELECT province_id, province_name, province_no FROM mat.province WHERE admin_version=2 LIMIT 5")).fetchall()
    for r in rows: print(f"  id={r[0]}, name={r[1]}, no={r[2]}")

# Doc file GSO raw bytes de phan tich encoding
prov_file = os.path.join(base, 'nso-gov-province_25_04_2026.csv')
with open(prov_file, 'rb') as f:
    raw = f.read(300)
print("\n=== RAW BYTES analysis ===")
print(repr(raw))

# Thu voi cp1258 (Vietnamese Windows)
import chardet
detected = chardet.detect(raw)
print(f"\nchardet detection: {detected}")
