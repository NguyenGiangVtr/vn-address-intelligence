"""
Fix notes font loi + cap nhat province_no/ward_no tu GOV
Strategy:
1. Notes bi loi TCVN3 encoding -> Clear notes cu, generate notes sach
   dua tren decision_number da parse duoc (ASCII ok)
2. province_no v2: cap nhat tu ma GOV (01->1, 04->4...) thay vi ma noi bo (10065...)  
3. ward_no: da dung ma noi bo, giua nguyen - lay ward_no tu file v2 CSV
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import re
from src.database import engine
from sqlalchemy import text

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

# Mapping GOV code -> standard province name (ASCII keys = GOV codes)
# Dung de generate notes sach
GSO_PROVINCE_INFO = {
    1:  {'name': 'Hà Nội',             'note': 'Giữ nguyên, không sắp xếp'},
    4:  {'name': 'Cao Bằng',           'note': 'Giữ nguyên, không sắp xếp'},
    8:  {'name': 'Tuyên Quang',        'note': 'Sáp nhập toàn bộ tỉnh Hà Giang vào tỉnh Tuyên Quang'},
    11: {'name': 'Điện Biên',          'note': 'Giữ nguyên, không sắp xếp'},
    12: {'name': 'Lai Châu',           'note': 'Giữ nguyên, không sắp xếp'},
    14: {'name': 'Sơn La',             'note': 'Sáp nhập toàn bộ tỉnh Sơn La vào tỉnh Yên Bái'},
    15: {'name': 'Yên Bái',            'note': 'Sáp nhập toàn bộ tỉnh Sơn La vào tỉnh Yên Bái'},
    19: {'name': 'Thái Nguyên',        'note': 'Sáp nhập toàn bộ tỉnh Bắc Kạn vào tỉnh Thái Nguyên'},
    20: {'name': 'Lạng Sơn',           'note': 'Sáp nhập toàn bộ tỉnh Lạng Sơn và tỉnh Bắc Giang'},
    22: {'name': 'Quảng Ninh',         'note': 'Giữ nguyên, không sắp xếp'},
    24: {'name': 'Bắc Giang',          'note': 'Sáp nhập vào tỉnh Lạng Sơn'},
    25: {'name': 'Phú Thọ',            'note': 'Sáp nhập toàn bộ tỉnh Vĩnh Phúc vào tỉnh Phú Thọ'},
    31: {'name': 'Hải Phòng',          'note': 'Sáp nhập tỉnh Hải Dương vào Hải Phòng'},
    33: {'name': 'Hưng Yên',           'note': 'Sáp nhập toàn bộ tỉnh Hưng Yên và tỉnh Hà Nam'},
    37: {'name': 'Ninh Bình',          'note': 'Sáp nhập toàn bộ tỉnh Nam Định vào tỉnh Ninh Bình'},
    38: {'name': 'Thanh Hóa',          'note': 'Giữ nguyên, không sắp xếp'},
    40: {'name': 'Nghệ An',            'note': 'Sáp nhập toàn bộ tỉnh Hà Tĩnh vào tỉnh Nghệ An'},
    42: {'name': 'Hà Tĩnh',            'note': 'Sáp nhập vào tỉnh Nghệ An'},
    44: {'name': 'Quảng Bình',         'note': 'Sáp nhập toàn bộ tỉnh Quảng Trị vào tỉnh Quảng Bình'},
    46: {'name': 'Thừa Thiên Huế',     'note': 'Trở thành TP Huế trực thuộc Trung ương'},
    48: {'name': 'Đà Nẵng',            'note': 'Sáp nhập tỉnh Quảng Nam vào Đà Nẵng'},
    51: {'name': 'Quảng Ngãi',         'note': 'Sáp nhập tỉnh Bình Định vào Quảng Ngãi'},
    52: {'name': 'Bình Định',          'note': 'Sáp nhập vào Quảng Ngãi'},
    56: {'name': 'Khánh Hòa',          'note': 'Sáp nhập tỉnh Phú Yên và Ninh Thuận vào Khánh Hòa'},
    66: {'name': 'Đắk Lắk',           'note': 'Sáp nhập tỉnh Đắk Nông vào Đắk Lắk'},
    68: {'name': 'Lâm Đồng',           'note': 'Sáp nhập tỉnh Bình Thuận vào Lâm Đồng'},
    75: {'name': 'Đồng Nai',           'note': 'Sáp nhập tỉnh Bà Rịa-Vũng Tàu vào Đồng Nai'},
    79: {'name': 'Hồ Chí Minh',        'note': 'Sáp nhập tỉnh Bình Dương và Tây Ninh vào TP.HCM'},
    80: {'name': 'Long An',            'note': 'Sáp nhập tỉnh Tiền Giang vào Long An'},
    82: {'name': 'Tiền Giang',         'note': 'Sáp nhập vào Long An'},
    86: {'name': 'Vĩnh Long',          'note': 'Sáp nhập tỉnh Trà Vinh vào Vĩnh Long'},
    91: {'name': 'Kiên Giang',         'note': 'Sáp nhập tỉnh An Giang vào Kiên Giang'},
    92: {'name': 'Cần Thơ',            'note': 'Sáp nhập tỉnh Hậu Giang và Sóc Trăng vào Cần Thơ'},
    96: {'name': 'Cà Mau',             'note': 'Sáp nhập tỉnh Bạc Liêu vào Cà Mau'},
}

print("=" * 60)
print("STEP 1: Fix notes cho province (admin_version=2)")
print("=" * 60)

# Doc decision number tu file GOV (phan ASCII doc OK)
df_prov = pd.read_csv(os.path.join(base, 'nso-gov-province_25_04_2026.csv'),
                      encoding='latin1', on_bad_lines='skip')
cols_p = list(df_prov.columns)

# Build map: gso_code -> decision info
gso_decision_map = {}
for _, row in df_prov.iterrows():
    try:
        code = int(row[cols_p[0]])
        decision_raw = str(row[cols_p[4]]) if pd.notna(row[cols_p[4]]) else ''
        # Chi lay phan ASCII (so nghi dinh va ngay)
        dec_match = re.search(r'(\d+/\d+/[A-Z0-9\-]+)', decision_raw)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', decision_raw)
        gso_decision_map[code] = {
            'decision_number': dec_match.group(1) if dec_match else (decision_raw[:50] if decision_raw else None),
            'decision_date': date_match.group(1) if date_match else None,
        }
    except: pass

with engine.connect() as conn:
    # Lay tat ca provinces tu DB
    db_provs = conn.execute(text(
        "SELECT province_id, province_name FROM mat.province WHERE admin_version=2"
    )).fetchall()
    
    count = 0
    for pid, pname in db_provs:
        # Tim GSO code tuong ung
        gso_code = None
        for code, info in GSO_PROVINCE_INFO.items():
            if pname and info['name'].lower() == pname.lower():
                gso_code = code
                break
        
        if not gso_code: continue
        
        note = GSO_PROVINCE_INFO[gso_code]['note']
        dec_info = gso_decision_map.get(gso_code, {})
        dec_num = dec_info.get('decision_number')
        dec_date_str = dec_info.get('decision_date')
        
        dec_date = None
        if dec_date_str:
            try:
                dec_date = pd.to_datetime(dec_date_str, dayfirst=True)
            except: pass
        
        # Update voi notes sach (tieng Viet dung)
        conn.execute(text("""
            UPDATE mat.province 
            SET notes = :n, decision_number = :dn, decision_date = :dd
            WHERE province_id = :pid AND admin_version = 2
        """), {'n': note, 'dn': dec_num, 'dd': dec_date, 'pid': pid})
        
        print(f"  Updated: {pname} -> note='{note[:60]}...'")
        count += 1
    
    conn.commit()
    print(f"Total updated provinces: {count}")

print("\n" + "=" * 60)
print("STEP 2: Cap nhat province_no cho province v2 (dung ma GOV)")
print("=" * 60)

with engine.connect() as conn:
    db_provs = conn.execute(text(
        "SELECT province_id, province_name, province_no FROM mat.province WHERE admin_version=2"
    )).fetchall()
    
    count = 0
    for pid, pname, old_no in db_provs:
        # Tim ma GOV tuong ung
        gso_code = None
        for code, info in GSO_PROVINCE_INFO.items():
            if pname and info['name'].lower() == pname.lower():
                gso_code = code
                break
        
        if gso_code and str(old_no) != str(gso_code):
            conn.execute(text("""
                UPDATE mat.province SET province_no = :pno
                WHERE province_id = :pid AND admin_version = 2
            """), {'pno': gso_code, 'pid': pid})
            print(f"  {pname}: province_no {old_no} -> {gso_code}")
            count += 1
    
    conn.commit()
    print(f"Total updated province_no: {count}")

print("\n" + "=" * 60)
print("STEP 3: Fix notes cho ward (admin_version=2, decision_number IS NOT NULL)")
print("=" * 60)

# Voi ward: clear garbled notes, thay bang text sach tu file GOV
# Notes ward chi la ghi chu nghi dinh, ta se clear va de NULL 
# hoac generate tu decision_number da co
# Vi file GOV ward co notes tieng Viet bi loi, ta se:
# 1. Clear notes hien tai (garbled)
# 2. Set notes la ten decision chuan

df_ward = pd.read_csv(os.path.join(base, 'nso-gov-ward_25_04_2026.csv'),
                      encoding='latin1', on_bad_lines='skip')
cols_w = list(df_ward.columns)

print(f"Ward CSV: {df_ward.shape[0]} rows, cols: {cols_w}")

with engine.connect() as conn:
    # Clear garbled notes trong ward v2 (chi xoa nhung cai co ky tu loi)
    r = conn.execute(text("""
        UPDATE mat.ward 
        SET notes = NULL
        WHERE admin_version = 2 
          AND notes IS NOT NULL
          AND notes ~ '[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F]'
    """))
    print(f"Cleared {r.rowcount} garbled ward notes (control chars)")
    
    # Also clear notes co ky tu '?' nhieu (dau hieu font loi)
    r = conn.execute(text(r"""
        UPDATE mat.ward 
        SET notes = NULL
        WHERE admin_version = 2
          AND notes IS NOT NULL
          AND length(notes) - length(replace(notes, '?', '')) > 5
    """))
    print(f"Cleared {r.rowcount} more garbled ward notes ('?' pattern)")
    
    conn.commit()

# Update ward_no tu file GOV (cot 0 = ma GSO 5 so)
print("\nUpdating ward_no from GOV file...")
with engine.connect() as conn:
    count = 0
    for _, row in df_ward.iterrows():
        try:
            ward_gso_code = str(row[cols_w[0]]).strip().zfill(5)
            prov_gso_code = int(row[cols_w[6]]) if pd.notna(row[cols_w[6]]) else None
            if not ward_gso_code.isdigit() or not prov_gso_code: continue
            if prov_gso_code not in GSO_PROVINCE_INFO: continue
            
            prov_name = GSO_PROVINCE_INFO[prov_gso_code]['name']
            
            # Update ward_no = ma GOV cho ward thuoc tinh nay trong admin_version=2
            r = conn.execute(text("""
                UPDATE mat.ward w
                SET ward_no = :wno
                FROM mat.district d, mat.province p
                WHERE w.district_id = d.district_id
                  AND d.province_id = p.province_id
                  AND w.admin_version = 2
                  AND LOWER(p.province_name) = LOWER(:pn)
                  AND (w.ward_id::text = :wgso OR w.ward_no = :wgso)
            """), {'wno': ward_gso_code, 'pn': prov_name, 'wgso': ward_gso_code})
            count += r.rowcount
        except: pass
    
    if count > 0: conn.commit()
    print(f"Updated {count} ward_no values")

print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT province_id, province_name, province_no, decision_number, 
               LEFT(notes, 60) as notes_preview
        FROM mat.province WHERE admin_version=2 LIMIT 5
    """)).fetchall()
    print("Province v2 sample:")
    for r in rows:
        print(f"  id={r[0]}, name={r[1]}, no={r[2]}, dec={r[3]}")
        print(f"  notes={r[4]}")
    
    ec = conn.execute(text("SELECT COUNT(*) FROM mat.province WHERE admin_version=2 AND notes IS NOT NULL")).scalar()
    ew = conn.execute(text("SELECT COUNT(*) FROM mat.ward WHERE admin_version=2 AND notes IS NOT NULL")).scalar()
    print(f"\nProvince v2 with clean notes: {ec}")
    print(f"Ward v2 with notes (clean): {ew}")
    
    garbled = conn.execute(text(r"""
        SELECT COUNT(*) FROM mat.ward 
        WHERE admin_version=2 AND notes IS NOT NULL
          AND length(notes) - length(replace(notes, '?', '')) > 5
    """)).scalar()
    print(f"Ward v2 still garbled notes: {garbled}")

print("\nDONE!")
