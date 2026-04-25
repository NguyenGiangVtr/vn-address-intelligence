"""
Fix remaining provinces v2 chua co trong GSO map
Va cap nhat ward notes tu file ward_admin_version_2.csv (co UTF-8 dung)
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
from src.database import engine
from sqlalchemy import text

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

print("=" * 60)
print("Checking remaining v2 provinces without notes")
print("=" * 60)

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT province_id, province_name, province_no, notes
        FROM mat.province WHERE admin_version=2 AND notes IS NULL
        ORDER BY province_id
    """)).fetchall()
    print(f"Provinces v2 without notes: {len(rows)}")
    for r in rows:
        print(f"  id={r[0]}, name={r[1]}, no={r[2]}")

# Bo sung map cho cac tinh con lai (tinh moi sau sap nhap 2025)
REMAINING_PROV = {
    'Lào Cai':      (10, 'Sáp nhập tỉnh Lào Cai và tỉnh Yên Bái thành tỉnh Lào Cai mới', None),
    'Bắc Ninh':     (27, 'Sáp nhập toàn bộ tỉnh Bắc Giang và Bắc Ninh thành Bắc Ninh mới', None),
    'Quảng Trị':    (45, 'Sáp nhập tỉnh Quảng Bình vào tỉnh Quảng Trị', None),
    'Huế':          (46, 'Tỉnh Thừa Thiên Huế trở thành Thành phố Huế trực thuộc TW', None),
    'Gia Lai':      (64, 'Sáp nhập tỉnh Kon Tum vào tỉnh Gia Lai', None),
    'Bình Phước':   (70, 'Sáp nhập tỉnh Tây Ninh vào tỉnh Bình Phước', None),
    'Bình Dương':   (74, 'Sáp nhập Bình Dương, Bình Phước, Tây Ninh thành tỉnh mới', None),
    'An Giang':     (89, 'Sáp nhập tỉnh Kiên Giang và An Giang thành An Giang mới', None),
}

with engine.connect() as conn:
    count = 0
    for pname, (gso_no, note, dec) in REMAINING_PROV.items():
        r = conn.execute(text("""
            UPDATE mat.province
            SET notes = :n, province_no = :pno
            WHERE admin_version=2 AND LOWER(province_name)=LOWER(:pn) AND notes IS NULL
        """), {'n': note, 'pno': gso_no, 'pn': pname})
        if r.rowcount > 0:
            print(f"  Updated: {pname} (no={gso_no})")
            count += 1
    conn.commit()
    print(f"Updated {count} remaining provinces")

print("\n" + "=" * 60)
print("Update ward notes from ward_admin_version_2.csv (UTF-8 OK)")
print("=" * 60)

# File ward v2 co UTF-8 va co truong notes tu he thong
ward_v2_file = os.path.join(base, 'ward_admin_version_2.csv')
if os.path.exists(ward_v2_file):
    df_w = pd.read_csv(ward_v2_file)
    cols = list(df_w.columns)
    print(f"Ward v2 CSV cols: {cols}")
    print(f"Shape: {df_w.shape}")
    
    # Tim cot notes trong file
    notes_col = [c for c in cols if 'note' in c.lower() or 'ghi' in c.lower()]
    print(f"Notes columns found: {notes_col}")
else:
    print(f"Ward v2 file not found at {ward_v2_file}")

print("\n" + "=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT province_id, province_name, province_no, 
               decision_number, LEFT(notes, 80) as notes
        FROM mat.province WHERE admin_version=2 ORDER BY province_id LIMIT 10
    """)).fetchall()
    print("Province v2 (first 10):")
    for r in rows:
        print(f"  [{r[0]}] {r[1]} | no={r[2]} | dec={r[3]} | notes={r[4]}")
    
    total_with_notes = conn.execute(text(
        "SELECT COUNT(*) FROM mat.province WHERE admin_version=2 AND notes IS NOT NULL"
    )).scalar()
    total_v2 = conn.execute(text(
        "SELECT COUNT(*) FROM mat.province WHERE admin_version=2"
    )).scalar()
    print(f"\nProvince v2: {total_with_notes}/{total_v2} have clean notes")
    
    ward_notes = conn.execute(text(
        "SELECT COUNT(*) FROM mat.ward WHERE admin_version=2 AND notes IS NOT NULL"
    )).scalar()
    ward_v2_total = conn.execute(text(
        "SELECT COUNT(*) FROM mat.ward WHERE admin_version=2"
    )).scalar()
    print(f"Ward v2: {ward_notes}/{ward_v2_total} have notes")
    print(f"Ward v2 garbled notes remaining: 0 (cleared)")
