"""
Enrichment GSO Gov bang NAME MATCHING
Vi ma GSO Gov khac hoan toan voi ma noi bo trong DB, 
ta se match bang ten don vi hanh chinh.
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import re
from src.database import engine
from sqlalchemy import text

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

def parse_decision(txt):
    if not txt or pd.isna(txt): return None, None
    s = str(txt)
    num_m = re.search(r'(\d+/[^\s,;-]+)', s)
    dec_num = num_m.group(1) if num_m else s[:100]
    date_m = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', s)
    dec_date = None
    if date_m:
        try: dec_date = pd.to_datetime(date_m.group(1), dayfirst=True)
        except: pass
    return dec_num, dec_date

def clean_name(name):
    """Loai bo prefix 'Tinh ', 'Thanh pho ', 'Phuong ', 'Xa '... de so khop ten."""
    if not name or pd.isna(name): return ''
    s = str(name).strip()
    # Loai bo prefix hanh chinh
    for prefix in ['Tỉnh ', 'Thành phố ', 'Thành Phố ', 'TP. ', 'TP ',
                    'Quận ', 'Huyện ', 'Thị xã ', 'Thành phố ',
                    'Phường ', 'Xã ', 'Thị trấn ']:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s.strip()

# ============================
# ENRICH PROVINCES BY NAME
# ============================
print("=" * 60)
print("ENRICHING PROVINCES BY NAME")
print("=" * 60)

df_p = pd.read_csv(os.path.join(base, 'nso-gov-province_25_04_2026.csv'), encoding='latin1', on_bad_lines='skip')
cols = list(df_p.columns)

with engine.connect() as conn:
    # Lay tat ca province tu DB
    db_provs = conn.execute(text("SELECT province_id, province_name FROM mat.province")).fetchall()
    
    count = 0
    for _, row in df_p.iterrows():
        gso_name = clean_name(str(row[cols[1]]))  # col[1] = Ten
        decision = row[cols[4]] if len(cols) > 4 else None
        notes = str(row[cols[5]]).strip() if len(cols) > 5 and pd.notna(row[cols[5]]) else None
        
        dec_num, dec_date = parse_decision(decision)
        
        # Tim province trong DB co ten tuong tu
        for db_id, db_name in db_provs:
            db_clean = clean_name(db_name)
            if db_clean and gso_name and db_clean.lower() == gso_name.lower():
                r = conn.execute(text("""
                    UPDATE mat.province SET decision_number = :dn, decision_date = :dd, notes = :n
                    WHERE province_id = :pid
                """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'pid': db_id})
                if r.rowcount > 0:
                    count += 1
                    print(f"  Matched: {gso_name} -> province_id={db_id}")
                break
    conn.commit()
    print(f"Total enriched provinces: {count}")

# ============================
# ENRICH WARDS BY NAME + PROVINCE
# ============================
print("\n" + "=" * 60)
print("ENRICHING WARDS BY NAME + PROVINCE")
print("=" * 60)

df_w = pd.read_csv(os.path.join(base, 'nso-gov-ward_25_04_2026.csv'), encoding='latin1', on_bad_lines='skip')
cols_w = list(df_w.columns)

with engine.connect() as conn:
    count = 0
    for i, row in df_w.iterrows():
        gso_ward_name = clean_name(str(row[cols_w[1]]))  # col[1] = Ten ward
        decision = row[cols_w[4]] if len(cols_w) > 4 else None
        notes = str(row[cols_w[5]]).strip() if len(cols_w) > 5 and pd.notna(row[cols_w[5]]) else None
        gso_prov_name = clean_name(str(row[cols_w[7]])) if len(cols_w) > 7 and pd.notna(row[cols_w[7]]) else None
        
        if not gso_ward_name: continue
        
        dec_num, dec_date = parse_decision(decision)
        
        # Match ward by name + province name (dam bao chinh xac)
        if gso_prov_name:
            r = conn.execute(text("""
                UPDATE mat.ward w SET decision_number = :dn, decision_date = :dd, notes = :n
                FROM mat.district d, mat.province p
                WHERE w.district_id = d.district_id AND d.province_id = p.province_id
                  AND LOWER(w.ward_name) = LOWER(:wn)
                  AND LOWER(p.province_name) LIKE LOWER(:pn)
            """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'wn': gso_ward_name, 'pn': f'%{gso_prov_name}%'})
        else:
            r = conn.execute(text("""
                UPDATE mat.ward SET decision_number = :dn, decision_date = :dd, notes = :n
                WHERE LOWER(ward_name) = LOWER(:wn)
            """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'wn': gso_ward_name})
        
        count += r.rowcount
        
        if i > 0 and i % 500 == 0:
            conn.commit()
            print(f"  Processed {i} wards ({count} updated)...")
    conn.commit()
    print(f"Total enriched wards: {count}")

# ============================
# VERIFICATION
# ============================
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    for name, q in {
        "Provinces enriched": "SELECT COUNT(*) FROM mat.province WHERE decision_number IS NOT NULL",
        "Wards enriched": "SELECT COUNT(*) FROM mat.ward WHERE decision_number IS NOT NULL",
        "Province NaN code remaining": "SELECT COUNT(*) FROM mat.province WHERE province_code = 'nan' OR province_code = 'NaN'",
    }.items():
        val = conn.execute(text(q)).scalar()
        print(f"  {name:35}: {val}")

print("\nDONE!")
