"""
Fix 2 tinh con lai + update ward notes tu GOV ward file (dung decision text)
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import re
from src.database import engine
from sqlalchemy import text

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

print("=" * 60)
print("Fix 2 remaining provinces: Tay Ninh, Dong Thap")
print("=" * 60)

with engine.connect() as conn:
    fixes = [
        ('Tây Ninh',   10090, 'Sáp nhập tỉnh Tây Ninh vào TP. Hồ Chí Minh'),
        ('Đồng Tháp',  10095, 'Sáp nhập tỉnh Đồng Tháp và tỉnh An Giang thành tỉnh An Giang mới'),
    ]
    for pname, old_no, note in fixes:
        r = conn.execute(text("""
            UPDATE mat.province SET notes = :n
            WHERE admin_version=2 AND LOWER(province_name)=LOWER(:pn)
        """), {'n': note, 'pn': pname})
        print(f"  {pname}: {r.rowcount} rows updated")
    conn.commit()

print("\n" + "=" * 60)
print("Update ward notes from GOV ward file (decision text ASCII ok)")
print("=" * 60)

# Doc file ward GOV - phan ASCII (decision number) doc duoc, phan notes tieng Viet bi loi
# Strategy: chi lay decision_number/date tu ASCII, bo qua notes text (bi loi encoding)
# Ward notes se set la: f"Nghi dinh {decision_number}" - chi thong tin chinh sach

df_w = pd.read_csv(os.path.join(base, 'nso-gov-ward_25_04_2026.csv'),
                   encoding='latin1', on_bad_lines='skip')
cols = list(df_w.columns)
print(f"Cols: {cols}")

# Map GOV prov code -> name
GSO_PROV_NAMES = {
    1:'Hà Nội',4:'Cao Bằng',8:'Tuyên Quang',11:'Điện Biên',12:'Lai Châu',
    14:'Sơn La',15:'Yên Bái',19:'Thái Nguyên',20:'Lạng Sơn',22:'Quảng Ninh',
    24:'Bắc Giang',25:'Phú Thọ',26:'Vĩnh Phúc',27:'Bắc Ninh',30:'Hải Dương',
    31:'Hải Phòng',33:'Hưng Yên',34:'Thái Bình',35:'Hà Nam',36:'Nam Định',
    37:'Ninh Bình',38:'Thanh Hóa',40:'Nghệ An',42:'Hà Tĩnh',44:'Quảng Bình',
    45:'Quảng Trị',46:'Thừa Thiên Huế',48:'Đà Nẵng',49:'Quảng Nam',
    51:'Quảng Ngãi',52:'Bình Định',54:'Phú Yên',56:'Khánh Hòa',58:'Ninh Thuận',
    60:'Bình Thuận',62:'Kon Tum',64:'Gia Lai',66:'Đắk Lắk',67:'Đắk Nông',
    68:'Lâm Đồng',70:'Bình Phước',72:'Tây Ninh',74:'Bình Dương',75:'Đồng Nai',
    77:'Bà Rịa - Vũng Tàu',79:'Hồ Chí Minh',80:'Long An',82:'Tiền Giang',
    83:'Bến Tre',84:'Trà Vinh',86:'Vĩnh Long',87:'Đồng Tháp',89:'An Giang',
    91:'Kiên Giang',92:'Cần Thơ',93:'Hậu Giang',94:'Sóc Trăng',95:'Bạc Liêu',96:'Cà Mau',
}

with engine.connect() as conn:
    count = 0
    for _, row in df_w.iterrows():
        ward_code = str(row[cols[0]]).strip().zfill(5)
        decision_raw = str(row[cols[4]]) if pd.notna(row[cols[4]]) else ''
        prov_gso = int(row[cols[6]]) if pd.notna(row[cols[6]]) else None
        
        if not ward_code.isdigit() or not prov_gso: continue
        prov_name = GSO_PROV_NAMES.get(prov_gso)
        if not prov_name: continue
        
        # Trich xuat decision number (ASCII ok)
        dec_match = re.search(r'(\d+/[A-Z0-9\-]+)', decision_raw)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', decision_raw)
        
        dec_num = dec_match.group(1) if dec_match else None
        dec_date = None
        if date_match:
            try: dec_date = pd.to_datetime(date_match.group(1), dayfirst=True)
            except: pass
        
        if not dec_num: continue
        
        # Tao notes sach tu decision info (khong dung text tieng Viet bi loi)
        note = f"Nghị quyết {dec_num}"
        if dec_date: note += f" ngày {dec_date.strftime('%d/%m/%Y')}"
        
        r = conn.execute(text("""
            UPDATE mat.ward w
            SET notes = :n, decision_number = :dn, decision_date = :dd,
                admin_version = 2
            FROM mat.district d, mat.province p
            WHERE w.district_id = d.district_id
              AND d.province_id = p.province_id
              AND w.ward_no = :wno
              AND LOWER(p.province_name) = LOWER(:pn)
        """), {'n': note, 'dn': dec_num, 'dd': dec_date, 'wno': ward_code, 'pn': prov_name})
        count += r.rowcount

    conn.commit()
    print(f"Updated {count} ward notes")

print("\n" + "=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    # Province final
    p_total = conn.execute(text("SELECT COUNT(*) FROM mat.province WHERE admin_version=2")).scalar()
    p_notes = conn.execute(text("SELECT COUNT(*) FROM mat.province WHERE admin_version=2 AND notes IS NOT NULL")).scalar()
    p_no_ok = conn.execute(text("SELECT COUNT(*) FROM mat.province WHERE admin_version=2 AND province_no < 100")).scalar()
    
    # Ward final
    w_total = conn.execute(text("SELECT COUNT(*) FROM mat.ward WHERE admin_version=2")).scalar()
    w_notes = conn.execute(text("SELECT COUNT(*) FROM mat.ward WHERE admin_version=2 AND notes IS NOT NULL")).scalar()
    w_dec = conn.execute(text("SELECT COUNT(*) FROM mat.ward WHERE admin_version=2 AND decision_number IS NOT NULL")).scalar()
    
    print(f"Province v2: {p_notes}/{p_total} with notes | {p_no_ok} with correct GOV province_no (<100)")
    print(f"Ward v2: {w_notes}/{w_total} with notes | {w_dec} with decision_number")
    
    print("\nSample province v2:")
    rows = conn.execute(text("""
        SELECT province_name, province_no, decision_number, notes
        FROM mat.province WHERE admin_version=2 ORDER BY province_no LIMIT 6
    """)).fetchall()
    for r in rows:
        print(f"  {r[0]:20} | no={r[1]:3} | dec={str(r[2])[:20]} | notes={str(r[3])[:60] if r[3] else 'NULL'}")
    
    print("\nSample ward v2 with notes:")
    rows = conn.execute(text("""
        SELECT w.ward_name, w.ward_no, w.decision_number, w.notes
        FROM mat.ward w WHERE w.admin_version=2 AND w.notes IS NOT NULL LIMIT 4
    """)).fetchall()
    for r in rows:
        print(f"  {str(r[0])[:25]} | no={r[1]} | dec={r[2]} | notes={str(r[3])[:60]}")

print("\nALL DONE!")
