"""
Enrichment Final: Su dung ma GSO + mapping thu cong
File GSO Gov bi hong encoding, nhung ma so (01, 04, 08...) van doc duoc.
Ta se tao mapping GSO_code -> province_id/province_name tu database,
sau do update decision_number va notes.
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import re
from src.database import engine
from sqlalchemy import text

# GSO standard code -> province name mapping (63 tinh chuan quoc gia)
GSO_PROVINCE_MAP = {
    1: 'Hà Nội', 2: 'Hà Giang', 4: 'Cao Bằng', 6: 'Bắc Kạn', 8: 'Tuyên Quang',
    10: 'Lào Cai', 11: 'Điện Biên', 12: 'Lai Châu', 14: 'Sơn La', 15: 'Yên Bái',
    17: 'Hòa Bình', 19: 'Thái Nguyên', 20: 'Lạng Sơn', 22: 'Quảng Ninh',
    24: 'Bắc Giang', 25: 'Phú Thọ', 26: 'Vĩnh Phúc', 27: 'Bắc Ninh',
    30: 'Hải Dương', 31: 'Hải Phòng', 33: 'Hưng Yên', 34: 'Thái Bình',
    35: 'Hà Nam', 36: 'Nam Định', 37: 'Ninh Bình', 38: 'Thanh Hóa',
    40: 'Nghệ An', 42: 'Hà Tĩnh', 44: 'Quảng Bình', 45: 'Quảng Trị',
    46: 'Thừa Thiên Huế', 48: 'Đà Nẵng', 49: 'Quảng Nam', 51: 'Quảng Ngãi',
    52: 'Bình Định', 54: 'Phú Yên', 56: 'Khánh Hòa', 58: 'Ninh Thuận',
    60: 'Bình Thuận', 62: 'Kon Tum', 64: 'Gia Lai', 66: 'Đắk Lắk',
    67: 'Đắk Nông', 68: 'Lâm Đồng', 70: 'Bình Phước', 72: 'Tây Ninh',
    74: 'Bình Dương', 75: 'Đồng Nai', 77: 'Bà Rịa - Vũng Tàu',
    79: 'Hồ Chí Minh', 80: 'Long An', 82: 'Tiền Giang', 83: 'Bến Tre',
    84: 'Trà Vinh', 86: 'Vĩnh Long', 87: 'Đồng Tháp', 89: 'An Giang',
    91: 'Kiên Giang', 92: 'Cần Thơ', 93: 'Hậu Giang', 94: 'Sóc Trăng',
    95: 'Bạc Liêu', 96: 'Cà Mau',
}

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

def parse_decision(txt):
    if not txt or pd.isna(txt): return None, None
    s = str(txt)
    num_m = re.search(r'(\d+/[^\s,;]+)', s)
    dec_num = num_m.group(1) if num_m else s[:100]
    date_m = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', s)
    dec_date = None
    if date_m:
        try: dec_date = pd.to_datetime(date_m.group(1), dayfirst=True)
        except: pass
    return dec_num, dec_date

# ============================
# ENRICH PROVINCES
# ============================
print("=" * 60)
print("ENRICHING PROVINCES")
print("=" * 60)

df_p = pd.read_csv(os.path.join(base, 'nso-gov-province_25_04_2026.csv'), encoding='latin1', on_bad_lines='skip')
cols = list(df_p.columns)

with engine.connect() as conn:
    # Build province_name -> province_id map from DB
    db_provs = conn.execute(text("SELECT province_id, province_name FROM mat.province")).fetchall()
    name_to_ids = {}
    for pid, pname in db_provs:
        if pname:
            key = pname.strip().lower()
            if key not in name_to_ids:
                name_to_ids[key] = []
            name_to_ids[key].append(pid)
    
    count = 0
    for _, row in df_p.iterrows():
        gso_code = int(row[cols[0]]) if pd.notna(row[cols[0]]) else None
        if not gso_code or gso_code not in GSO_PROVINCE_MAP: continue
        
        prov_name = GSO_PROVINCE_MAP[gso_code]
        decision = row[cols[4]] if len(cols) > 4 else None
        notes = str(row[cols[5]]).strip() if len(cols) > 5 and pd.notna(row[cols[5]]) else None
        
        dec_num, dec_date = parse_decision(decision)
        
        # Match by name in DB
        key = prov_name.strip().lower()
        pids = name_to_ids.get(key, [])
        
        for pid in pids:
            r = conn.execute(text("""
                UPDATE mat.province SET decision_number = :dn, decision_date = :dd, notes = :n
                WHERE province_id = :pid
            """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'pid': pid})
            if r.rowcount > 0:
                count += 1
                print(f"  OK: GSO {gso_code:02d} -> {prov_name} (pid={pid})")
    conn.commit()
    print(f"Total enriched provinces: {count}")

# ============================
# ENRICH WARDS
# ============================
print("\n" + "=" * 60)
print("ENRICHING WARDS")
print("=" * 60)

df_w = pd.read_csv(os.path.join(base, 'nso-gov-ward_25_04_2026.csv'), encoding='latin1', on_bad_lines='skip')
cols_w = list(df_w.columns)

with engine.connect() as conn:
    count = 0
    for i, row in df_w.iterrows():
        decision = row[cols_w[4]] if len(cols_w) > 4 else None
        notes = str(row[cols_w[5]]).strip() if len(cols_w) > 5 and pd.notna(row[cols_w[5]]) else None
        
        # Province code from GSO
        gso_prov_code = int(row[cols_w[6]]) if len(cols_w) > 6 and pd.notna(row[cols_w[6]]) else None
        if not gso_prov_code or gso_prov_code not in GSO_PROVINCE_MAP: continue
        
        prov_name = GSO_PROVINCE_MAP[gso_prov_code]
        dec_num, dec_date = parse_decision(decision)
        
        # Ward GSO code (5 digits)
        ward_gso_code = str(row[cols_w[0]]).strip().zfill(5)
        
        # Match ward by ward_no (GSO code) AND province_name
        r = conn.execute(text("""
            UPDATE mat.ward w SET decision_number = :dn, decision_date = :dd, notes = :n
            FROM mat.district d, mat.province p
            WHERE w.district_id = d.district_id AND d.province_id = p.province_id
              AND w.ward_no = :wno
              AND LOWER(p.province_name) = LOWER(:pn)
        """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'wno': ward_gso_code, 'pn': prov_name})
        count += r.rowcount
        
        if i > 0 and i % 500 == 0:
            conn.commit()
            print(f"  Processed {i} wards ({count} updated)...")
    conn.commit()
    print(f"Total enriched wards: {count}")

# ============================
# Also fix remaining NaN issues
# ============================
print("\n" + "=" * 60)
print("FIXING REMAINING NaN")
print("=" * 60)

with engine.connect() as conn:
    for tbl, col in [('mat.province','province_no'), ('mat.province','served_radius'),
                     ('mat.district','district_no'), ('mat.ward','ward_no')]:
        r = conn.execute(text(f"UPDATE {tbl} SET {col} = NULL WHERE {col} = 'nan' OR {col} = 'NaN'"))
        if r.rowcount > 0: print(f"  Fixed {r.rowcount} NaN in {tbl}.{col}")
    conn.commit()

# ============================
# FINAL VERIFICATION
# ============================
print("\n" + "=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    for name, q in {
        "Provinces total": "SELECT COUNT(*) FROM mat.province",
        "Provinces enriched (decision)": "SELECT COUNT(*) FROM mat.province WHERE decision_number IS NOT NULL",
        "Provinces NaN code": "SELECT COUNT(*) FROM mat.province WHERE province_no = 'nan'",
        "Wards total": "SELECT COUNT(*) FROM mat.ward",
        "Wards enriched (decision)": "SELECT COUNT(*) FROM mat.ward WHERE decision_number IS NOT NULL",
        "Ward Mappings": "SELECT COUNT(*) FROM mat.ward_mapping",
        "OSM raw_entities": "SELECT COUNT(*) FROM osm.raw_entities",
        "Training datasets": "SELECT COUNT(*) FROM ath.training_datasets",
        "Address queue": "SELECT COUNT(*) FROM prq.address_cleansing_queue",
    }.items():
        val = conn.execute(text(q)).scalar()
        print(f"  {name:35}: {val:>10}")

print("\nALL DONE!")
